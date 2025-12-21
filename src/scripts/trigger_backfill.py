# src/scripts/trigger_backfill.py
import sys
from src.collector.news import JobManager

def main():
    if len(sys.argv) < 3:
        print("Usage: python src/scripts/trigger_backfill.py <stock_code> <days>")
        sys.exit(1)
    
    stock_code = sys.argv[1]
    days = int(sys.argv[2])
    
    manager = JobManager()
    job_id = manager.create_backfill_job(stock_code, days)
    print(f"Successfully triggered backfill job {job_id} for {stock_code} ({days} days)")

if __name__ == "__main__":
    main()
