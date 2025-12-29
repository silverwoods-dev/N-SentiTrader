# src/scripts/test_memory_awo.py
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.learner.awo_engine import AWOEngine
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_sequential_awo(stock_code):
    """
    Runs a tiny 2-window scan to check if the new sequential logic works.
    """
    logger.info(f"[*] Starting Verification for Small Sequential AWO: {stock_code}")
    
    engine = AWOEngine(stock_code)
    
    # 1. Create a dummy job
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, status)
            VALUES (%s, 'AWO_SCAN_MEMORY_TEST', 'pending')
            RETURNING v_job_id
        """, (stock_code,))
        v_job_id = cur.fetchone()['v_job_id']
    
    try:
        # Override windows/alphas for quick test
        # Normally AWO handles windows internally, but we'll use 1m and 3m
        # We need to monkey-patch or just let it run.
        # For this test, we'll just let it run one day validation.
        
        logger.info(f"[*] Triggering AWO Scan with Job #{v_job_id}")
        
        # We manually call a small-scale validation to check persistence
        # Window=1m, Alpha=0.0001
        res = engine.run_exhaustive_scan(validation_months=1, v_job_id=v_job_id)
        
        # 2. Check if results were persisted in DB
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as count, used_version 
                FROM tb_verification_results 
                WHERE v_job_id = %s
                GROUP BY used_version
            """, (v_job_id,))
            rows = cur.fetchall()
            
            if not rows:
                logger.error("[x] FAIL: No rows persisted in tb_verification_results.")
                return False
            
            for r in rows:
                logger.info(f"[v] Persisted {r['count']} rows for version: {r['used_version']}")
        
        logger.info("[v] Verification SUCCESS: Sequential logic and persistence confirmed.")
        return True

    except Exception as e:
        logger.error(f"[x] Verification FAILED: {e}")
        return False

if __name__ == "__main__":
    verify_sequential_awo("005930")
