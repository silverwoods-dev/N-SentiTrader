# src/scripts/verify_walk_forward.py
import argparse
import logging
from datetime import datetime, timedelta
from src.learner.validator import WalkForwardValidator

def main():
    parser = argparse.ArgumentParser(description="N-SentiTrader Walk-forward Validation Runner")
    parser.add_argument("--stock", type=str, default="005930", help="Stock code to validate")
    parser.add_argument("--days", type=int, default=30, help="Number of days to validate (backwards from today)")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    validator = WalkForwardValidator(args.stock)
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=args.days)
    
    logging.info(f"Starting validation for {args.stock} over {args.days} days...")
    results = validator.run_validation(start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
    
    if results:
        hit_rate = sum(1 for r in results if r['is_correct']) / len(results)
        print("\n" + "="*40)
        print(f"Validation Result for {args.stock}")
        print(f"Period: {start_date} ~ {end_date}")
        print(f"Total Trading Days: {len(results)}")
        print(f"Hit Rate: {hit_rate:.2%}")
        print("="*40)
    else:
        print("No validation results generated. Check data availability.")

if __name__ == "__main__":
    main()
