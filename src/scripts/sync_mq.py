# src/scripts/sync_mq.py
import json
import logging
from src.db.connection import get_db_cursor
from src.utils.mq import get_mq_channel, JOB_QUEUE_NAME, VERIFICATION_QUEUE_NAME, publish_job, publish_verification_job

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync_queues():
    logger.info("Starting MQ Sync Process...")
    
    # 1. Purge Queues to remove ghost messages
    # Note: We use get_mq_channel which ensures queues are declared
    for q_name in [JOB_QUEUE_NAME, VERIFICATION_QUEUE_NAME]:
        conn, ch = get_mq_channel(q_name)
        try:
            ch.queue_purge(queue=q_name)
            logger.info(f"Purged queue: {q_name}")
        finally:
            conn.close()

    # 2. Re-enqueue Pending Jobs from tb_verification_jobs
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT v_job_id, stock_code, v_type, params 
            FROM tb_verification_jobs 
            WHERE status = 'pending'
        """)
        v_jobs = cur.fetchall()
        
        for job in v_jobs:
            params = job['params'] if isinstance(job['params'], dict) else json.loads(job['params'] or '{}')
            v_payload = {
                "v_type": job['v_type'],
                "stock_code": job['stock_code'],
                "v_job_id": job['v_job_id'],
                "val_months": params.get('val_months', 1)
            }
            publish_verification_job(v_payload)
            logger.info(f"Re-enqueued Verification Job #{job['v_job_id']} for {job['stock_code']}")

    # 3. Re-enqueue Pending Jobs from jobs (Collection/Backfill)
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT job_id, params 
            FROM jobs 
            WHERE status = 'pending'
        """)
        c_jobs = cur.fetchall()
        
        for job in c_jobs:
            params = job['params'] if isinstance(job['params'], dict) else json.loads(job['params'] or '{}')
            # Ensure job_id is in params
            params['job_id'] = job['job_id']
            publish_job(params)
            logger.info(f"Re-enqueued Collection Job #{job['job_id']}")

    logger.info("MQ Sync Process Completed.")

if __name__ == "__main__":
    sync_queues()
