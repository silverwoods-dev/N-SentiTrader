# src/tools/recover_system.py
import logging
import json
import requests
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.utils.mq import MQ_HOST, MQ_USER, MQ_PASS, JOB_QUEUE_NAME, VERIFICATION_QUEUE_NAME, DAILY_JOB_QUEUE_NAME

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RecoverSystem")

def check_mq_consumers():
    """Verify consumers on critical queues"""
    try:
        url = f"http://{MQ_HOST}:15672/api/queues"
        response = requests.get(url, auth=(MQ_USER, MQ_PASS), timeout=5)
        if response.status_code == 200:
            queues = response.json()
            logger.info("--- RabbitMQ Consumer Status ---")
            for q in queues:
                name = q['name']
                consumers = q['consumers']
                ready = q['messages_ready']
                logger.info(f"Queue: {name:<20} | Consumers: {consumers:<3} | Ready: {ready}")
            return queues
    except Exception as e:
        logger.error(f"Failed to check MQ: {e}")
    return []

def recover_stale_jobs(threshold_minutes=30):
    """Mark stale running jobs as pending to allow retry"""
    logger.info(f"--- Recovering Stale Jobs (threshold: {threshold_minutes}m) ---")
    cutoff = datetime.now() - timedelta(minutes=threshold_minutes)
    
    with get_db_cursor() as cur:
        # 1. General Jobs
        cur.execute("""
            UPDATE jobs 
            SET status = 'pending', message = 'Recovered by system tool', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'running' AND updated_at < %s
            RETURNING job_id, job_type
        """, (cutoff,))
        recovered_jobs = cur.fetchall()
        for r in recovered_jobs:
            logger.info(f"Recovered Job #{r['job_id']} ({r['job_type']})")

        # 2. Verification Jobs
        cur.execute("""
            UPDATE tb_verification_jobs 
            SET status = 'pending', updated_at = CURRENT_TIMESTAMP
            WHERE status = 'running' AND updated_at < %s
            RETURNING v_job_id, v_type
        """, (cutoff,))
        recovered_v = cur.fetchall()
        for r in recovered_v:
            logger.info(f"Recovered Verification Job #{r['v_job_id']} ({r['v_type']})")
        
        logger.info(f"Total Recovered: {len(recovered_jobs) + len(recovered_v)}")

def main():
    logger.info("=== N-SentiTrader System Recovery Tool ===")
    
    # 1. Mark stale jobs as pending
    recover_stale_jobs(threshold_minutes=15)
    
    # 2. Check current consumer state
    check_mq_consumers()
    
    logger.info("=== Recovery Task Completed ===")

if __name__ == "__main__":
    main()
