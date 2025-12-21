
import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.learner.awo_engine import AWOEngine
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_promotion():
    stock_code = "005930"
    engine = AWOEngine(stock_code)
    
    # 1. Force deactivate everything first (sanity check)
    with get_db_cursor() as cur:
        cur.execute("UPDATE tb_sentiment_dict_meta SET is_active = FALSE WHERE stock_code = %s", (stock_code,))
        
    logger.info(">>> Deactivated all versions for verification.")
    
    # 2. Run promote_best_model (Simulating 1-month window found)
    # This should train a new model and activate it.
    logger.info(">>> Running promote_best_model(1)...")
    res = engine.promote_best_model(1)
    
    if res['status'] != 'success':
        logger.error(f"Promotion returned failure: {res}")
        return False
        
    new_version = res['version']
    logger.info(f">>> Promotion reports success. New version: {new_version}")
    
    # 3. Verify in DB
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT is_active, version 
            FROM tb_sentiment_dict_meta 
            WHERE stock_code = %s AND version = %s
        """, (stock_code, new_version))
        row = cur.fetchone()
        
        if not row:
            logger.error(">>> New version NOT found in DB.")
            return False
            
        if row['is_active']:
            logger.info(">>> SUCCESS: New version is active.")
            return True
        else:
            logger.error(">>> FAILURE: New version found but is_active=FALSE.")
            return False

if __name__ == "__main__":
    if verify_promotion():
        print("VERIFICATION PASSED")
        sys.exit(0)
    else:
        print("VERIFICATION FAILED")
        sys.exit(1)
