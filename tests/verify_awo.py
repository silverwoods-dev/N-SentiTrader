
import sys
import os
import logging
from datetime import datetime, timedelta

# Update path to include project root
sys.path.append(os.getcwd())

from src.learner.awo_engine import AWOEngine
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_awo_scan(stock_code="005930"):
    print(f"--- Starting AWO Integration Test for {stock_code} ---")
    
    # 1. Initialize Engine
    engine = AWOEngine(stock_code)
    
    # 2. Run Scan (Short validation window for test speed)
    print("Running 2D Exhaustive Scan (Window x Alpha)...")
    summary = engine.run_exhaustive_scan(validation_months=1)
    
    if summary:
        print("\n--- Scan Results ---")
        print(f"Best Window: {summary['best_window']}m")
        print(f"Best Alpha: {summary['best_alpha']}")
        print(f"Best Stability Score: {summary['best_stability_score']:.4f}")
        print(f"Max Hit Rate: {summary['hit_rate']:.2%}")
        
        print("\n--- Detailed Scores (First 5) ---")
        count = 0
        for k, v in summary['all_scores'].items():
            print(f"{k}: HR={v['hit_rate']:.2%}, Stab={v['stability_score']:.4f}")
            count += 1
            if count >= 5: break
            
        # Check Promotion
        if summary.get("promotion"):
            print(f"\nPromotion Status: {summary['promotion'].get('status')}")
            if summary['promotion'].get('status') == 'success':
                 print(f"Promoted Version: {summary['promotion'].get('version')}")
        
    else:
        print("Scan failed or returned None.")

if __name__ == "__main__":
    verify_awo_scan()
