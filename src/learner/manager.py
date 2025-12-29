# src/learner/manager.py
import polars as pl
from datetime import datetime, timedelta
from src.learner.lasso import LassoLearner
from src.db.connection import get_db_cursor
import logging

logger = logging.getLogger(__name__)

class AnalysisManager:
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.learner = LassoLearner()

    def check_data_availability(self, days_needed=90):
        """
        최소 3개월(90일) 이상의 뉴스 및 가격 데이터가 있는지 확인합니다.
        """
        with get_db_cursor() as cur:
            # 주가 데이터 확인
            cur.execute("""
                SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date 
                FROM tb_daily_price WHERE stock_code = %s
            """, (self.stock_code,))
            price_row = cur.fetchone()
            
            # 뉴스 데이터 확인
            cur.execute("""
                SELECT COUNT(DISTINCT c.published_at::date) as date_count
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s
            """, (self.stock_code,))
            news_row = cur.fetchone()
            
        if not price_row or not news_row:
            return False, 0
            
        days_span = (price_row['max_date'] - price_row['min_date']).days
        news_days = news_row['date_count']
        
        logger.info(f"Data Check for {self.stock_code}: Price Days={days_span}, News Days={news_days}")
        
        # 주가와 정보가 모두 일정 기간 이상 있어야 함
        return (days_span >= days_needed - 10 and news_days >= days_needed * 0.5), days_span

    def run_daily_update(self, v_job_id=None):
        """
        매일 실행되는 버퍼 사전 업데이트 (최근 7일)
        """
        if v_job_id:
            logger.info(f"Connecting Daily Update (Job #{v_job_id}) to DB...")
            self._update_job_status(v_job_id, 'running', 10)

        logger.info(f"Running daily buffer update for {self.stock_code}")
        
        # [MEMORY_OPT] Check for Golden Parameters for Lightweight Retraining (TASK-046)
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT optimal_lag, optimal_window_months, optimal_alpha 
                FROM daily_targets WHERE stock_code = %s
            """, (self.stock_code,))
            row = cur.fetchone()
        
        end_date = datetime.now().date()
        
        if row and row['optimal_window_months']:
            # --- [Lightweight Retraining Strategy] ---
            # Use verified Golden Parameters from AWO Scan
            window = int(row['optimal_window_months'])
            alpha = float(row['optimal_alpha'])
            lag = int(row['optimal_lag'])
            
            logger.info(f"  [LightUpdate] Using Golden Params: Window={window}m, Alpha={alpha}, Lag={lag}")
            
            # 1. Main Dictionary Update (Using full window)
            m_start = end_date - timedelta(days=window * 30)
            self.learner.run_training(
                self.stock_code,
                m_start.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                version="daily_main_light",
                source="Main",
                alpha=alpha,
                lags=lag
            )
            
            # 2. Daily Buffer Update (7 days)
            b_start = end_date - timedelta(days=7)
            self.learner.run_training(
                self.stock_code,
                b_start.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                version="daily_buffer_light",
                source="Buffer",
                alpha=alpha,
                lags=lag
            )
            logger.info(f"  [v] Lightweight Retraining completed in seconds for {self.stock_code}")
        else:
            # Fallback to standard 7-day buffer update if no AWO scan has been done
            logger.warning(f"  [LightUpdate] No Golden Params found for {self.stock_code}. Fallback to standard 7d buffer.")
            start_date = end_date - timedelta(days=7)
            self.learner.run_training(
                self.stock_code, 
                start_date.strftime('%Y-%m-%d'), 
                end_date.strftime('%Y-%m-%d'), 
                version="daily_buffer", 
                source="Buffer"
            )
        
        if v_job_id:
            self._update_job_status(v_job_id, 'completed', 100)
            
        return True

    def run_full_pipeline(self, v_job_id=None):
        """
        1. 데이터 확인
        2. 최적 시차 도출
        3. Main Dictionary 학습 (2개월)
        4. Buffer Dictionary 초기 학습 (1주일)
        """
        if v_job_id:
            self._update_job_status(v_job_id, 'running', 5)

        available, days = self.check_data_availability(90)
        if not available:
            logger.warning(f"Not enough data for {self.stock_code} ({days} days found).")
            if v_job_id:
                self._update_job_status(v_job_id, 'failed', 0, summary={"error": "Insufficient data", "days": days})
            return False

        if v_job_id: self._update_job_status(v_job_id, 'running', 20)

        # 날짜 계산
        end_date = datetime.now().date()
        train_end = end_date - timedelta(days=1)
        train_start = train_end - timedelta(days=60)
        
        t_start_str = train_start.strftime('%Y-%m-%d')
        t_end_str = train_end.strftime('%Y-%m-%d')

        logger.info(f"Starting full pipeline for {self.stock_code}: Train({t_start_str}~{t_end_str})")

        # 1. 최적 시차 도출
        optimal_lag = self.learner.find_optimal_lag(self.stock_code, t_start_str, t_end_str)
        self.learner.lags = optimal_lag
        
        if v_job_id: self._update_job_status(v_job_id, 'running', 50)

        # 2. Main Dictionary 학습
        self.learner.run_training(self.stock_code, t_start_str, t_end_str, version="v1_main", source="Main")
        
        if v_job_id: self._update_job_status(v_job_id, 'running', 80)

        # 3. Buffer Dictionary 초기 학습
        self.run_daily_update()

        if v_job_id:
            self._update_job_status(v_job_id, 'completed', 100)

        return True

    def run_walkforward_check(self, val_months=1, v_job_id=None):
        """단순 워크포워드 검증 수행 (AWO Scan 아님)"""
        from src.learner.validator import WalkForwardValidator
        import json
        
        if v_job_id:
            self._update_job_status(v_job_id, 'running', 10)
            
        validator = WalkForwardValidator(self.stock_code)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=val_months * 30)
        
        res = validator.run_validation(
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            train_days=60, # 기본값
            dry_run=True
        )
        
        if v_job_id:
            summary = {
                "hit_rate": res['hit_rate'],
                "mae": res['mae'],
                "total_days": res['total_days']
            }
            self._update_job_status(v_job_id, 'completed', 100, summary=summary)
            
            # 상세 결과 저장
            self._save_verification_results(v_job_id, res['results'])
            
        return res

    def _save_verification_results(self, v_job_id, results):
        """상세 결과를 DB에 저장"""
        from src.db.connection import get_db_cursor
        with get_db_cursor() as cur:
            for r in results:
                cur.execute("""
                    INSERT INTO tb_verification_results 
                    (v_job_id, target_date, predicted_score, actual_alpha, is_correct, used_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (v_job_id, r['date'], r['sentiment_score'], r['actual_alpha'], r['is_correct'], 'WF_CHECK'))

    def _update_job_status(self, v_job_id, status, progress, summary=None):
        import json
        with get_db_cursor() as cur:
            if summary:
                cur.execute("""
                    UPDATE tb_verification_jobs 
                    SET status = %s, progress = %s, result_summary = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE v_job_id = %s
                """, (status, progress, json.dumps(summary), v_job_id))
            else:
                cur.execute("""
                    UPDATE tb_verification_jobs 
                    SET status = %s, progress = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE v_job_id = %s
                """, (status, progress, v_job_id))
        
        # Prometheus Update
        try:
            from src.utils.metrics import BACKTEST_PROGRESS, BACKTEST_JOBS_BY_STATUS
            # Update status gauge
            if status in ['pending', 'running', 'completed', 'failed', 'stopped']:
                # Note: This is a bit tricky since we don't have the full count here.
                # But we can at least signal progress.
                pass
            
            BACKTEST_PROGRESS.labels(job_id=str(v_job_id), stock_code=self.stock_code).set(progress)
            
            # If terminal state, we might want to cleanup later, 
            # but for now just setting it to 100 or 0 is fine.
        except:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    am = AnalysisManager("005930")
    am.run_full_pipeline()
