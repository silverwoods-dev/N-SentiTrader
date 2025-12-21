# src/learner/awo_engine.py
import logging
from datetime import datetime, timedelta
from src.learner.validator import WalkForwardValidator
from src.db.connection import get_db_cursor
import json

logger = logging.getLogger(__name__)

class AWOEngine:
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.validator = WalkForwardValidator(stock_code)

    def run_exhaustive_scan(self, validation_months=1, v_job_id=None):
        """
        1단계: 전수 스캐닝 (Exhaustive Initial Scan)
        1개월부터 11개월까지 학습 윈도우를 변경해가며 최근 N개월 성과를 전수 조사합니다.
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=validation_months * 30)
        
        results = {}
        
        # 1. Verification Job 등록 (v_job_id가 없을 때만)
        if v_job_id is None:
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO tb_verification_jobs (stock_code, v_type, params, status)
                    VALUES (%s, 'AWO_SCAN', %s, 'running')
                    RETURNING v_job_id
                """, (self.stock_code, json.dumps({"range": "1-11m", "val_months": validation_months})))
                v_job_id = cur.fetchone()['v_job_id']
        else:
            # 기존 Job 상태를 running으로 업데이트
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE tb_verification_jobs SET status = 'running', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                    (v_job_id,)
                )

        try:
            for months in range(1, 12):
                # 중단 요청 확인
                if self._is_stopped(v_job_id):
                    logger.info(f"AWO Scan stopped by user for {self.stock_code} (Job #{v_job_id})")
                    return None

                logger.info(f"Scanning window: {months} months for {self.stock_code}...")
                train_days = months * 30
                
                # Check stop signal
                with get_db_cursor() as cur:
                    cur.execute("SELECT status FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
                    row = cur.fetchone()
                    if row and row['status'] == 'stopped':
                        logger.info(f"AWO Scan stopped by user: {v_job_id}")
                        return

                # WalkForwardValidator를 사용하여 해당 윈도우 성과 측정
                res = self.validator.run_validation(
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    train_days=train_days,
                    dry_run=True  # 검증용 예측치이므로 메인 predictions 테이블에는 넣지 않음
                )
                
                results[months] = {
                    "hit_rate": res['hit_rate'],
                    "mae": res['mae']
                }
                
                # 상세 결과 저장
                if res['results']:
                    self.save_scan_results(v_job_id, months, res['results'])
                
                # 진행률 업데이트 및 하트비트
                progress = (months / 11) * 100
                with get_db_cursor() as cur:
                    cur.execute(
                        "UPDATE tb_verification_jobs SET progress = %s, updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                        (progress, v_job_id)
                    )

            # 2. 결과 요약 및 최적 윈도우 도출
            if not results:
                raise ValueError("No results generated during scan.")
                
            # Hit Rate가 가장 높은 윈도우 선택 (동일할 경우 MAE가 낮은 쪽)
            best_window = max(results, key=lambda k: (results[k]['hit_rate'], -results[k]['mae']))
            summary = {
                "best_window_months": best_window,
                "max_hit_rate": results[best_window]['hit_rate'],
                "min_mae": results[best_window]['mae'],
                "scan_results": results
            }
            
            with get_db_cursor() as cur:
                cur.execute("""
                    UPDATE tb_verification_jobs 
                    SET status = 'completed', result_summary = %s, progress = 100, completed_at = CURRENT_TIMESTAMP
                    WHERE v_job_id = %s
                """, (json.dumps(summary), v_job_id))
            
            logger.info(f"AWO Scan completed. Best: {best_window}m (Hit Rate: {results[best_window]['hit_rate']:.2%}, MAE: {results[best_window]['mae']:.4f})")
            
            # 3. Promotion Phase: 최적 윈도우로 실운영 모델 재학습
            self.promote_best_model(best_window)
            
            return summary

        except Exception as e:
            logger.error(f"AWO Scan failed for {self.stock_code}: {e}")
            with get_db_cursor() as cur:
                cur.execute("SELECT retry_count FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
                row = cur.fetchone()
                current_retries = row['retry_count'] if row else 0
                
                if current_retries < 2: # Max 2 retries for heavy AWO Scan
                    cur.execute(
                        "UPDATE tb_verification_jobs SET status = 'pending', retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                        (v_job_id,)
                    )
                    logger.info(f"AWO Job #{v_job_id} reset to pending for retry ({current_retries + 1}/2)")
                else:
                    cur.execute(
                        "UPDATE tb_verification_jobs SET status = 'failed', updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                        (v_job_id,)
                    )
                    logger.error(f"AWO Job #{v_job_id} failed after maximum retries.")
            raise e

    def promote_best_model(self, window_months):
        """최적 윈도우를 사용하여 최종 Production 모델을 학습하고 활성화함."""
        logger.info(f"Promoting best model for {self.stock_code} using {window_months}m window...")
        
        train_days = window_months * 30
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=train_days)
        
        # LassoLearner의 run_training을 사용하여 최종본 생성
        # version에 'prod' 접미사를 붙여 구분
        version = f"prod_{window_months}m_{end_date.strftime('%Y%m%d')}"
        
        try:
            self.validator.learner.run_training(
                self.stock_code,
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                version=version,
                source='Main'
            )
            logger.info(f"Model Promotion Successful: {version}")
        except Exception as e:
            logger.error(f"Model Promotion Failed: {e}")

    def save_scan_results(self, v_job_id, window_months, results):
        """윈도우별 검증 상세 결과를 tb_verification_results 에 기록"""
        with get_db_cursor() as cur:
            for r in results:
                cur.execute("""
                    INSERT INTO tb_verification_results 
                    (v_job_id, target_date, predicted_score, actual_alpha, is_correct, used_version)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (v_job_id, r['date'], r['sentiment_score'], r['actual_alpha'], r['is_correct'], f"{window_months}m_scan"))
    def _is_stopped(self, v_job_id):
        """작업이 중단 상태인지 확인"""
        with get_db_cursor() as cur:
            cur.execute("SELECT status FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
            row = cur.fetchone()
            return row and row['status'] == 'stopped'
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    stock = sys.argv[1] if len(sys.argv) > 1 else "005930"
    engine = AWOEngine(stock)
    engine.run_exhaustive_scan(validation_months=1)
