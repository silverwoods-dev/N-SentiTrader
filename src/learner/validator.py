# src/learner/validator.py
import polars as pl
import numpy as np
from datetime import datetime, timedelta
from src.learner.lasso import LassoLearner
from src.predictor.scoring import Predictor
from src.db.connection import get_db_cursor
import logging

logger = logging.getLogger(__name__)

class WalkForwardValidator:
    def __init__(self, stock_code, use_sector_beta=False):
        self.stock_code = stock_code
        self.use_sector_beta = use_sector_beta
        self.learner = LassoLearner(use_sector_beta=use_sector_beta)
        self.predictor = Predictor()

    def run_validation(self, start_date, end_date, train_days=60, dry_run=False, progress_callback=None):
        """
        start_date부터 end_date까지 하루씩 이동하며 예측 및 검증을 수행합니다.
        train_days: Main Dictionary 학습에 사용할 과거 일수
        dry_run: DB 저장을 건너뛸지 여부
        """
        logger.info(f"Starting Walk-forward validation for {self.stock_code}: {start_date} ~ {end_date} (Train Window: {train_days} days, Pure Alpha: {self.use_sector_beta}, Dry Run: {dry_run})")
        
        # 전체 검증 기간의 주가 데이터를 미리 가져옴
        with get_db_cursor() as cur:
            if self.use_sector_beta:
                sql = """
                    SELECT date, (return_rate - COALESCE(sector_return, 0)) as alpha 
                    FROM tb_daily_price 
                    WHERE stock_code = %s AND date BETWEEN %s AND %s
                    ORDER BY date ASC
                """
            else:
                sql = """
                    SELECT date, excess_return as alpha 
                    FROM tb_daily_price 
                    WHERE stock_code = %s AND date BETWEEN %s AND %s
                    ORDER BY date ASC
                """
            cur.execute(sql, (self.stock_code, start_date, end_date))
            actual_prices = {row['date'].strftime('%Y-%m-%d'): float(row['alpha']) for row in cur.fetchall()}

        validation_dates = sorted(actual_prices.keys())
        results = []

        for i, current_date_str in enumerate(validation_dates):
            if i == len(validation_dates) - 1:
                break # 마지막 날은 다음날 가격 데이터가 없으므로 예측만 가능하지만 검증은 불가
            
            # 1. 학습 구간 설정
            current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()
            train_end = current_date - timedelta(days=1)
            train_start = train_end - timedelta(days=train_days)
            
            # 2. Dictionary 시뮬레이션 학습
            # version 이름에 train_days를 포함하여 실험별 구분 가능하게 함
            version = f"val_{train_days}d_{current_date_str}"
            
            try:
                # Main Dictionary 학습 (현재 시점 기준 train_days 기간)
                self.learner.run_training(
                    self.stock_code, 
                    train_start.strftime('%Y-%m-%d'),
                    train_end.strftime('%Y-%m-%d'),
                    version=version,
                    source='Main'
                )
                
                # Daily Buffer 업데이트 (최근 7일)
                self.learner.run_training(
                    self.stock_code,
                    (current_date - timedelta(days=7)).strftime('%Y-%m-%d'),
                    train_end.strftime('%Y-%m-%d'),
                    version=version,
                    source='Buffer'
                )

                # 3. 예측 수행 (오늘의 뉴스로 내일의 가격 예측)
                news_by_lag = self.fetch_historical_news_by_lag(current_date, lag_limit=self.learner.lags)
                fundamentals = self.fetch_historical_fundamentals(current_date)
                
                # 뉴스나 펀더멘털 중 하나라도 있으면 예측 시도 (Hybrid)
                if not news_by_lag and not fundamentals:
                    # logger.warning(f"  [{current_date_str}] No data found for prediction.")
                    continue
                    
                pred_res = self.predictor.predict_advanced(self.stock_code, news_by_lag, version, fundamentals=fundamentals)
                
                # If everything is zero/observation, skip
                if pred_res['status'] == "Observation":
                    continue
                
                # Status is used as the directional signal (Strong Buy, Cautious Buy -> 1)
                prediction = 1 if "Buy" in pred_res['status'] else (0 if "Sell" in pred_res['status'] else None)
                expected_alpha = pred_res['expected_alpha']
                
                # 4. 실제값과 비교 (다음 거래일의 수익률)
                next_date_str = validation_dates[i+1]
                actual_alpha = actual_prices[next_date_str]
                
                is_correct = False
                if prediction is not None:
                    is_correct = (prediction == (1 if actual_alpha > 0 else 0))
                
                res_entry = {
                    "date": current_date_str,
                    "prediction": prediction or 0,
                    "sentiment_score": expected_alpha,
                    "actual_alpha": actual_alpha,
                    "is_correct": is_correct,
                    "top_keywords": pred_res.get('top_keywords', {})
                }
                results.append(res_entry)
                
                # 5. DB 기록
                if not dry_run:
                    self.save_validation_result(res_entry)
                
                if i % 5 == 0 or i == len(validation_dates) - 2:
                    logger.info(f"  [{current_date_str}] Pred: {res_entry['prediction']}, Actual Alpha: {actual_alpha:.4f}, Correct: {is_correct}")

                if progress_callback:
                    # 0.0 ~ 1.0
                    p = (i + 1) / len(validation_dates)
                    progress_callback(p)

            except Exception as e:
                logger.error(f"Error in validation loop for {current_date_str}: {e}")

        # 총평 출력
        if results:
            hit_rate = sum(1 for r in results if r['is_correct']) / len(results)
            mae = sum(abs(r['sentiment_score'] - r['actual_alpha']) for r in results) / len(results)
            logger.info(f"Validation Finished ({train_days}d). Total Days: {len(results)}, Hit Rate: {hit_rate:.2%}, MAE: {mae:.4f}")
            return {
                "train_days": train_days,
                "total_days": len(results),
                "hit_rate": hit_rate,
                "mae": mae,
                "results": results
            }
        return {"train_days": train_days, "total_days": 0, "hit_rate": 0, "mae": 0, "results": []}

    def fetch_historical_news_by_lag(self, target_date, lag_limit):
        from src.nlp.tokenizer import Tokenizer
        from src.utils.calendar import Calendar
        tokenizer = Tokenizer()
        news_by_lag = {}
        
        # 1. 대상 종목의 거래일 목록 가져오기
        trading_days = Calendar.get_trading_days(self.stock_code)
        if not trading_days:
            return {}

        # 2. 검증 대상일(target_date)의 인덱스 찾기
        idx = -1
        for i, d in enumerate(trading_days):
            if d == target_date:
                idx = i
                break
        
        if idx == -1:
            return {}

        with get_db_cursor() as cur:
            for lag in range(1, lag_limit + 1):
                if idx - (lag - 1) < 0:
                    break
                    
                actual_impact_date = trading_days[idx - (lag - 1)]
                prev_trading_day = trading_days[idx - lag] if idx - lag >= 0 else actual_impact_date - timedelta(days=7)
                
                # Impact Date Logic: (prev_trading_day) 16:00 <= published_at < (actual_impact_date) 16:00
                cur.execute("""
                    SELECT c.content
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s 
                      AND c.published_at >= %s::timestamp + interval '16 hours'
                      AND c.published_at < %s::timestamp + interval '16 hours'
                """, (self.stock_code, prev_trading_day, actual_impact_date))
                
                rows = cur.fetchall()
                tokens = []
                for row in rows:
                    if row['content']:
                        tokens.extend(tokenizer.tokenize(row['content']))
                
                if tokens:
                    news_by_lag[lag] = tokens
        return news_by_lag

    def fetch_historical_fundamentals(self, target_date):
        """특정 날짜 기준 가장 최근의 펀더멘털 데이터를 가져옵니다."""
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT per, pbr, roe, market_cap
                FROM tb_stock_fundamentals
                WHERE stock_code = %s AND base_date <= %s
                ORDER BY base_date DESC
                LIMIT 1
            """, (self.stock_code, target_date))
            row = cur.fetchone()
            
            if row:
                return {
                    'per': float(row['per']),
                    'pbr': float(row['pbr']),
                    'roe': float(row['roe']),
                    'market_cap': float(row['market_cap']),
                    # 'log_market_cap' 은 Predictor에서 계산함
                }
        return {}

    def save_validation_result(self, res):
        import json
        with get_db_cursor() as cur:
            cur.execute("""
                INSERT INTO tb_predictions (stock_code, prediction_date, sentiment_score, prediction, actual_alpha, is_correct, top_keywords)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (self.stock_code, res['date'], res['sentiment_score'], res['prediction'], res['actual_alpha'], res['is_correct'], json.dumps(res.get('top_keywords', {}))))
            # Note: tb_predictions 에 UNIQUE 제약조건이 없다면 ON CONFLICT 대신 DELETE 후 INSERT 필요
            # 현재 schema.sql 에는 UNIQUE 제약이 없으므로 단순 삽입하거나 수동으로 처리

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stock = "005930"
    v = WalkForwardValidator(stock)
    # 최근 30일간 검증
    end = datetime.now().date()
    start = end - timedelta(days=30)
    v.run_validation(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
