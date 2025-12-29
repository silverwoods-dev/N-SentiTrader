
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db.connection import get_db_cursor
from src.dashboard.data_helpers import get_stock_stats_data
from src.collector.news import JobManager

def verify_gap_feature():
    stock_code = "005930" # Samsung
    print(f"--- Verifying Gap Backfill for {stock_code} ---")
    
    with get_db_cursor() as cur:
        # 1. Identify bounds
        cur.execute("""
            SELECT MIN(published_at_hint) as min_date, MAX(published_at_hint) as max_date
            FROM tb_news_mapping nm
            JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
            WHERE nm.stock_code = %s
        """, (stock_code,))
        res = cur.fetchone()
        min_date, max_date = res['min_date'], res['max_date']
        print(f"Original Date Range: {min_date} ~ {max_date}")

        # 2. Simulate a gap (Delete news for a 3-day window in the middle)
        gap_start = min_date + timedelta(days=5)
        gap_end = gap_start + timedelta(days=2)
        print(f"Simulating gap from {gap_start} to {gap_end}")
        
        # We use a transaction to roll back later if we want, but here we just delete and verify.
        # Actually, better to just check detection WITHOUT deleting if possible, 
        # but a real delete is a better test.
        # Let's just SELECT dates to see if we can find existing gaps first.
        
    # Check current gaps
    with get_db_cursor() as cur:
        stats = get_stock_stats_data(cur, stock_code)
        if stats:
            s = stats[0]
            print(f"Detected Missing Days (Before): {s.get('missing_days', 0)}")
            
    # 3. Trigger Gap Backfill
    print("Triggering Gap Backfill...")
    manager = JobManager()
    count = manager.create_gap_backfill_jobs(stock_code)
    print(f"Jobs Created: {count}")
    
    if count > 0:
        with get_db_cursor() as cur:
            cur.execute("SELECT job_id, params FROM jobs WHERE job_type = 'backfill' ORDER BY job_id DESC LIMIT %s", (count,))
            new_jobs = cur.fetchall()
            for j in new_jobs:
                print(f"New Job ID: {j['job_id']}, Params: {j['params']}")

if __name__ == "__main__":
    verify_gap_feature()
