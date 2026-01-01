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
    def __init__(self, stock_code, use_sector_beta=False, model_type='tfidf'):
        self.stock_code = stock_code
        self.use_sector_beta = use_sector_beta
        self.model_type = model_type  # 'tfidf' or 'hybrid'
        self.learner = LassoLearner(use_sector_beta=use_sector_beta)
        self.predictor = Predictor()
        self.token_fetch_cache = {} # Persistent cache for news tokens by (date, stock_code)
        
        if model_type == 'hybrid':
            logger.info(f"[{stock_code}] Using HYBRID model (TF-IDF + BERT)")
        else:
            logger.info(f"[{stock_code}] Using TF-IDF only model")

    def run_validation(self, start_date, end_date, train_days=60, dry_run=False, progress_callback=None, v_job_id=None, prefetched_df_news=None, alpha=None, used_version_tag='v_job', retrain_frequency='weekly'):
        """
        start_date부터 end_date까지 하루씩 이동하며 예측 및 검증을 수행합니다.
        train_days: Main Dictionary 학습에 사용할 과거 일수
        dry_run: DB 저장을 건너뛸지 여부
        alpha: Lasso Regularization Strength (If None, use learner's default)
        used_version_tag: DB 기록 시 used_version 필드에 들어갈 값
        retrain_frequency: 'daily' | 'weekly' - Main 사전 재학습 빈도
        """
        if alpha is not None:
            self.learner.alpha = alpha
            if hasattr(self.learner.model, 'alpha'):
                self.learner.model.alpha = alpha
        
        logger.info(f"Starting Walk-forward validation for {self.stock_code}: {start_date} ~ {end_date} (Train Window: {train_days} days, Alpha: {self.learner.alpha}, Pure Alpha: {self.use_sector_beta}, Dry Run: {dry_run})")
        
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
        
        if prefetched_df_news is None:
            # --- Memory Optimization: Bulk News Fetching ---
            # Fetch all news for the entire range (lookback + test) once
            lookback_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=train_days + self.learner.lags + 2)).date()
            full_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            logger.info(f"  [Memory] Prefetching and tokenizing all news from {lookback_start} to {full_end}...")
            
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT c.published_at::date as date, c.content
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s AND c.published_at::date BETWEEN %s AND %s
                """, (self.stock_code, lookback_start, full_end))
                all_news_raw = cur.fetchall()
                
            df_all_news = pl.DataFrame(all_news_raw) if all_news_raw else pl.DataFrame({"date": [], "content": []})
            del all_news_raw # Clear raw list immediately
            
            # Pre-tokenize everything using LassoLearner's logic
            if not df_all_news.is_empty():
                from src.learner.lasso import TOKEN_CACHE as GLOBAL_TOKEN_CACHE
                
                def get_cached_tokens(content):
                    if content in GLOBAL_TOKEN_CACHE:
                        return GLOBAL_TOKEN_CACHE[content]
                    t = self.learner.tokenizer.tokenize(content, n_gram=self.learner.n_gram)
                    if len(GLOBAL_TOKEN_CACHE) < 50000:
                        GLOBAL_TOKEN_CACHE[content] = t
                    return t
                
                df_all_news = df_all_news.with_columns(
                    pl.col("content").map_elements(get_cached_tokens, return_dtype=pl.List(pl.String)).alias("tokens")
                )
            # -----------------------------------------------
        else:
            df_all_news = prefetched_df_news

        for i, current_date_str in enumerate(validation_dates):
            # Check for stop signal if v_job_id provided
            if v_job_id and i % 2 == 0: 
                with get_db_cursor() as cur:
                    cur.execute("SELECT status FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
                    row = cur.fetchone()
                    if not row or row['status'] == 'stopped':
                        logger.info(f"Validation loop stopped by user or missing job for {self.stock_code} (Job #{v_job_id})")
                        return {"train_days": train_days, "total_days": len(results), "hit_rate": 0, "mae": 0, "results": results, "status": "stopped"}

            if i == len(validation_dates) - 1:
                break # 마지막 날은 다음날 가격 데이터가 없으므로 예측만 가능하지만 검증은 불가
            
            # 1. 학습 구간 설정
            current_date = datetime.strptime(current_date_str, '%Y-%m-%d').date()
            train_end = current_date - timedelta(days=1)
            train_start = train_end - timedelta(days=train_days)
            
            # 2. Dictionary 시뮬레이션 학습
            version = f"val_{train_days}d_{current_date_str}"
            
            try:
                # Weekly Retraining Logic: Main 사전은 주 1회 (첫날 또는 월요일)
                should_retrain_main = False
                if retrain_frequency == 'daily':
                    should_retrain_main = True
                elif retrain_frequency == 'weekly':
                    # 첫 번째 날이거나 월요일인 경우 재학습
                    if i == 0 or current_date.weekday() == 0:  # Monday = 0
                        should_retrain_main = True
                else:  # monthly or other
                    if i == 0 or current_date.day == 1:
                        should_retrain_main = True
                
                if should_retrain_main:
                    # Main Dictionary 학습 (prefetched_df_news 주입)
                    self.learner.run_training(
                        self.stock_code, 
                        train_start.strftime('%Y-%m-%d'),
                        train_end.strftime('%Y-%m-%d'),
                        version=version,
                        source='Main',
                        prefetched_df_news=df_all_news
                    )
                
                # Daily Buffer 업데이트 (최근 7일) - 항상 실행 (경량 연산)
                self.learner.run_training(
                    self.stock_code,
                    (current_date - timedelta(days=7)).strftime('%Y-%m-%d'),
                    train_end.strftime('%Y-%m-%d'),
                    version=version,
                    source='Buffer',
                    prefetched_df_news=df_all_news
                )

                # 3. 예측 수행 (오늘의 뉴스로 내일의 가격 예측)
                news_by_lag = self.fetch_historical_news_by_lag(current_date, lag_limit=self.learner.lags, cache=self.token_fetch_cache)
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
                    self.save_validation_result(res_entry, v_job_id=v_job_id, used_version_tag=used_version_tag)
                
                if i % 5 == 0 or i == len(validation_dates) - 2:
                    logger.info(f"  [{current_date_str}] Pred: {res_entry['prediction']}, Actual Alpha: {actual_alpha:.4f}, Correct: {is_correct}")

                # MEMORY_OPT: Frequent GC in backtest loop
                if i % 2 == 0:
                    import gc
                    gc.collect()

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
        
        self.token_fetch_cache.clear() # Clear persistent cache for this run
        import gc
        gc.collect()
        
        return {"train_days": train_days, "total_days": 0, "hit_rate": 0, "mae": 0, "results": []}

    def fetch_historical_news_by_lag(self, target_date, lag_limit, cache=None):
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
                date_str = actual_impact_date.strftime('%Y-%m-%d')
                
                # Check cache
                if cache is not None and date_str in cache:
                    if cache[date_str]:
                        news_by_lag[lag] = cache[date_str]
                    continue

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
                        # Use LassoLearner's global TOKEN_CACHE if possible
                        from src.learner.lasso import TOKEN_CACHE as GLOBAL_TOKEN_CACHE
                        content = row['content']
                        if content in GLOBAL_TOKEN_CACHE:
                            tokens.extend(GLOBAL_TOKEN_CACHE[content])
                        else:
                            t = tokenizer.tokenize(content)
                            if len(GLOBAL_TOKEN_CACHE) < 10000:
                                GLOBAL_TOKEN_CACHE[content] = t
                            tokens.extend(t)
                
                if tokens:
                    news_by_lag[lag] = tokens
                    if cache is not None:
                        cache[date_str] = tokens
                else:
                    if cache is not None:
                        cache[date_str] = []
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

    def save_validation_result(self, res, v_job_id=None, used_version_tag='v_job'):
        import json
        with get_db_cursor() as cur:
            if v_job_id:
                # Backtest mode: Save to tb_verification_results
                cur.execute("""
                    INSERT INTO tb_verification_results (v_job_id, target_date, predicted_score, actual_alpha, is_correct, used_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (v_job_id, res['date'], res['sentiment_score'], res['actual_alpha'], res['is_correct'], used_version_tag))
            else:
                # Production/Manual mode: Save to tb_predictions
                cur.execute("""
                    INSERT INTO tb_predictions (stock_code, prediction_date, sentiment_score, prediction, actual_alpha, is_correct, top_keywords)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (self.stock_code, res['date'], res['sentiment_score'], res['prediction'], res['actual_alpha'], res['is_correct'], json.dumps(res.get('top_keywords', {}))))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stock = "005930"
    v = WalkForwardValidator(stock)
    # 최근 30일간 검증
    # 최근 데이터가 19일까지 있으므로
    end = datetime.strptime('2025-12-19', '%Y-%m-%d').date()
    start = end - timedelta(days=3)
    v.run_validation(start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'), train_days=14)
