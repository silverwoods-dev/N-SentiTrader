# src/learner/drift_monitor.py
import logging
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.learner.lasso import LassoLearner

logger = logging.getLogger(__name__)

class DriftMonitor:
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.learner = LassoLearner()

    def check_drift_and_rollback(self):
        """
        Check for model drift in the last 7 days and rollback if necessary.
        PRD 18.2: 7-day MovAvg Hit-Rate < 45% for 3 consecutive assessments.
        """
        logger.info(f"Checking drift for {self.stock_code}...")
        
        with get_db_cursor() as cur:
            # 1. Fetch last 10 days of prediction/settlement data to see trends
            cur.execute("""
                SELECT prediction_date, is_correct
                FROM tb_predictions
                WHERE stock_code = %s AND actual_alpha IS NOT NULL
                ORDER BY prediction_date DESC
                LIMIT 10
            """, (self.stock_code,))
            rows = cur.fetchall()
            
            if len(rows) < 7:
                logger.info(f"Insufficient settlement data for {self.stock_code} ({len(rows)}/7). Skipping drift check.")
                return False

            # Calculate 7-day moving averages (we need at least 3 points to check for '3 consecutive days')
            # But wait, '3 consecutive days' of what? If we check daily, we just need to know if the 7d MA is < 45% today, 
            # and it was < 45% yesterday and the day before.
            
            def get_window_hit_rate(data_slice):
                hits = sum(1 for r in data_slice if r['is_correct'])
                return hits / len(data_slice)

            # Check T, T-1, T-2 window (each window is 7 days)
            # T: 0-6
            # T-1: 1-7
            # T-2: 2-8
            
            if len(rows) < 9: # Need 9 days to have three 7-day windows
                logger.info(f"Insufficient data for consecutive drift check (Need 9 settled days).")
                return False

            hr_t0 = get_window_hit_rate(rows[0:7])
            hr_t1 = get_window_hit_rate(rows[1:8])
            hr_t2 = get_window_hit_rate(rows[2:9])
            
            logger.info(f"[{self.stock_code}] 7d Hit-Rates: T={hr_t0:.4f}, T-1={hr_t1:.4f}, T-2={hr_t2:.4f}")
            
            DRIFT_THRESHOLD = 0.45
            if hr_t0 < DRIFT_THRESHOLD and hr_t1 < DRIFT_THRESHOLD and hr_t2 < DRIFT_THRESHOLD:
                logger.warning(f"!!! MODEL DRIFT DETECTED for {self.stock_code} !!!")
                rollback_success = self.perform_rollback()
                
                # --- [Smart Pipeline: Proactive Calibration] ---
                # Trigger AWO 2D Scan to find better parameters for current regime
                try:
                    from src.utils.mq import publish_verification_job
                    import json
                    cur.execute("""
                        INSERT INTO tb_verification_jobs (stock_code, v_type, status, params)
                        VALUES (%s, 'AWO_SCAN_2D', 'pending', %s)
                        RETURNING v_job_id
                    """, (self.stock_code, json.dumps({"reason": "drift_detected", "val_months": 1})))
                    row = cur.fetchone()
                    if row:
                        v_job_id = row['v_job_id']
                        publish_verification_job({
                            "v_job_id": v_job_id,
                            "v_type": "AWO_SCAN_2D",
                            "stock_code": self.stock_code,
                            "val_months": 1
                        })
                        logger.info(f"Proactive AWO 2D Scan triggered for {self.stock_code} (Job #{v_job_id})")
                except Exception as e:
                    logger.error(f"Failed to trigger proactive AWO scan: {e}")
                # -----------------------------------------------
                
                return rollback_success
            
        return False

    def perform_rollback(self):
        """Rollback to parent_version of the currently active model."""
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT version, parent_version 
                FROM tb_sentiment_dict_meta
                WHERE stock_code = %s AND source = 'Main' AND is_active = TRUE
                ORDER BY created_at DESC LIMIT 1
            """, (self.stock_code,))
            row = cur.fetchone()
            
            if not row or not row['parent_version']:
                logger.error(f"No parent version found for {self.stock_code}. Rollback impossible.")
                return False
            
            current_ver = row['version']
            target_ver = row['parent_version']
            
            logger.info(f"Rolling back {self.stock_code}: {current_ver} -> {target_ver}")
            
            # Deactivate current, activate parent
            cur.execute("""
                UPDATE tb_sentiment_dict_meta
                SET is_active = FALSE
                WHERE stock_code = %s AND version = %s AND source = 'Main'
            """, (self.stock_code, current_ver))
            
            cur.execute("""
                UPDATE tb_sentiment_dict_meta
                SET is_active = TRUE
                WHERE stock_code = %s AND version = %s AND source = 'Main'
            """, (self.stock_code, target_ver))
            
            logger.info(f"Rollback successful for {self.stock_code}.")
            return True

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    stock = sys.argv[1] if len(sys.argv) > 1 else "005930"
    monitor = DriftMonitor(stock)
    monitor.check_drift_and_rollback()
