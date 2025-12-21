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
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.learner = LassoLearner()
        self.predictor = Predictor()

    def run_validation(self, start_date, end_date, train_days=60, dry_run=False):
        """
        start_date부터 end_date까지 하루씩 이동하며 예측 및 검증을 수행합니다.
        train_days: Main Dictionary 학습에 사용할 과거 일수
        dry_run: DB 저장을 건너뛸지 여부
        """
        logger.info(f"Starting Walk-forward validation for {self.stock_code}: {start_date} ~ {end_date} (Train Window: {train_days} days, Dry Run: {dry_run})")
        
        # 전체 검증 기간의 주가 데이터를 미리 가져옴
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT date, excess_return 
                FROM tb_daily_price 
                WHERE stock_code = %s AND date BETWEEN %s AND %s
                ORDER BY date ASC
            """, (self.stock_code, start_date, end_date))
            actual_prices = {row['date'].strftime('%Y-%m-%d'): float(row['excess_return']) for row in cur.fetchall()}

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
                
                if not news_by_lag:
                    # logger.warning(f"  [{current_date_str}] No news found for prediction.")
                    continue
                    
                pred_res = self.predictor.predict_advanced(self.stock_code, news_by_lag, version)
                
                # 4. 실제값과 비교 (다음 거래일의 수익률)
                next_date_str = validation_dates[i+1]
                actual_alpha = actual_prices[next_date_str]
                
                is_correct = (pred_res['prediction'] == (1 if actual_alpha > 0 else 0))
                
                res_entry = {
                    "date": current_date_str,
                    "prediction": pred_res['prediction'],
                    "sentiment_score": pred_res['total_score'],
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

            except Exception as e:
                logger.error(f"Error in validation loop for {current_date_str}: {e}")

        # 총평 출력
        if results:
            hit_rate = sum(1 for r in results if r['is_correct']) / len(results)
            logger.info(f"Validation Finished ({train_days}d). Total Days: {len(results)}, Hit Rate: {hit_rate:.2%}")
            return {
                "train_days": train_days,
                "total_days": len(results),
                "hit_rate": hit_rate,
                "results": results
            }
        return {"train_days": train_days, "total_days": 0, "hit_rate": 0, "results": []}

    def fetch_historical_news_by_lag(self, target_date, lag_limit):
        from src.nlp.tokenizer import Tokenizer
        tokenizer = Tokenizer()
        news_by_lag = {}
        
        with get_db_cursor() as cur:
            for i in range(1, lag_limit + 1):
                lag_date = target_date - timedelta(days=i-1)
                cur.execute("""
                    SELECT c.content
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s AND c.published_at::date = %s
                """, (self.stock_code, lag_date))
                rows = cur.fetchall()
                
                tokens = []
                for row in rows:
                    tokens.extend(tokenizer.tokenize(row['content']))
                
                if tokens:
                    news_by_lag[i] = tokens
        return news_by_lag

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
