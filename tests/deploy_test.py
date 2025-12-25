
import sys
import os
import logging
from datetime import datetime
import json

# Update path
sys.path.append(os.getcwd())

from src.learner.awo_engine import AWOEngine
from src.db.connection import get_db_cursor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Top 5 KOSPI Representation
# 005930 (Samsung Elec) - Semi/Tech
# 000660 (SK Hynix) - Semi
# 035420 (Naver) - Internet/Platform
# 207940 (Samsung Biologics) - Bio
# 005380 (Hyundai Motor) - Auto
TARGET_STOCKS = ["005930", "000660", "035420", "207940", "005380"]

def run_scalability_test():
    results = {}
    print(f"--- Starting Scalability Test on {len(TARGET_STOCKS)} Stocks ---")
    
    for code in TARGET_STOCKS:
        print(f"\n[Processing Stock: {code}]")
        try:
            engine = AWOEngine(code)
            # validation_months=1 for speed in verification phase (Production would be much longer)
            # We want to check if it runs without error and produces scores.
            summary = engine.run_exhaustive_scan(validation_months=1)
            
            if summary:
                results[code] = {
                    "status": "success",
                    "best_window": summary['best_window'],
                    "best_alpha": summary['best_alpha'],
                    "stability": summary['best_stability_score'],
                    "final_score": summary['all_scores'].get(f"{summary['best_window']}m_{summary['best_alpha']}")
                }
                print(f"  -> Success: W={summary['best_window']}m, A={summary['best_alpha']}, Stab={summary['best_stability_score']:.4f}")
            else:
                results[code] = {"status": "failed", "reason": "No summary returned"}
                print("  -> Failed: No summary")
                
        except Exception as e:
            results[code] = {"status": "error", "message": str(e)}
            print(f"  -> Error: {e}")
            
    # Print Validation Report
    print("\n--- Scalability Test Report ---")
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Save to file for review
    with open("tests/scalability_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    run_scalability_test()
