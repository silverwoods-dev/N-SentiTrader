# src/pipeline/master_orchestrator.py
import json
import logging
from src.utils.mq import publish_verification_job, publish_daily_job
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MasterOrchestrator:
    """
    Orchestrates the N-SentiTrader AI Pipeline.
    Manages the transitions between:
    1. NEWS_COLLECTION (Done by AddressWorker/BodyWorker)
    2. MARKET_DATA_SYNC (Hooked in NewsCollector)
    3. MODEL_TRAINING (Daily Buffer Update or AWO-2D)
    4. REPORT_GENERATION (Narrative Intelligence)
    """
    
    @staticmethod
    def trigger_stage_2_training(stock_code, v_type="DAILY_UPDATE"):
        """
        Triggered after News & Market Data Sync is complete.
        """
        logger.info(f"[Orchestrator] Triggering Stage 2 Training ({v_type}) for {stock_code}")
        
        with get_db_cursor() as cur:
            # Check for existing pending jobs to avoid duplicate execution
            cur.execute("""
                SELECT v_job_id FROM tb_verification_jobs 
                WHERE stock_code = %s AND v_type = %s AND status = 'pending'
            """, (stock_code, v_type))
            if cur.fetchone():
                logger.warning(f"[Orchestrator] Pending {v_type} for {stock_code} already exists. Skipping trigger.")
                return
            
            # Create a new verification job
            params = {"reason": "automated_master_pipeline_trigger"}
            cur.execute("""
                INSERT INTO tb_verification_jobs (stock_code, v_type, status, params)
                VALUES (%s, %s, 'pending', %s)
                RETURNING v_job_id
            """, (stock_code, v_type, json.dumps(params)))
            row = cur.fetchone()
            if row:
                v_job_id = row['v_job_id']
                publish_verification_job({
                    "v_job_id": v_job_id,
                    "v_type": v_type,
                    "stock_code": stock_code
                })
                logger.info(f"[Orchestrator] Successfully queued {v_type} #{v_job_id}")

    @staticmethod
    def trigger_stage_3_report(stock_code, target_date=None, v_job_id=None):
        """
        Triggered after Training is complete.
        Currently reports are dynamic on the dashboard, but we could 
        pre-generate narrative summaries here.
        """
        logger.info(f"[Orchestrator] Triggering Stage 3 Reporting for {stock_code}")
        # In the future, this can trigger sub-tasks like REQ-NARR generation
        pass

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        cmd = sys.argv[1]
        stock = sys.argv[2]
        if cmd == "train":
            MasterOrchestrator.trigger_stage_2_training(stock)
