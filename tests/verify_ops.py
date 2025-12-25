
import sys
import os
import logging
import json

sys.path.append(os.getcwd())

from src.predictor.scoring import Predictor
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_ops():
    print("--- Starting Operational Verification ---")
    
    predictor = Predictor()
    
    # Run daily prediction (Dry run effectively, but writes to DB)
    # We should use a test version or check DB after.
    # Since run_daily_prediction writes to tb_predictions, we check the latest insert.
    
    print("Running Predictor.run_daily_prediction()...")
    results = predictor.run_daily_prediction()
    
    print(f"Generated {len(results)} predictions.")
    
    if len(results) > 0:
        sample = results[0]
        print(f"Sample Prediction for {sample['stock_code']}:")
        print(f"  Status: {sample['status']}")
        print(f"  Score: {sample['net_score']:.4f}")
        print(f"  Conf: {sample['confidence_score']}")
        
        # Verify DB Insert
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT * FROM tb_predictions 
                WHERE stock_code = %s AND prediction_date = CURRENT_DATE
                ORDER BY created_at DESC LIMIT 1
            """, (sample['stock_code'],))
            row = cur.fetchone()
            
            if row:
                print("  [DB Verification] Success: Record found in tb_predictions.")
                print(f"  DB Status: {row['status']}")
            else:
                print("  [DB Verification] Failed: Record NOT found.")
                
    else:
        print("No predictions generated. Check if 'daily_targets' has active stocks.")

if __name__ == "__main__":
    verify_ops()
