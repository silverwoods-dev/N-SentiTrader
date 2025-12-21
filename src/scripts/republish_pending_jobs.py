# src/scripts/republish_pending_jobs.py
from src.db.connection import get_db_cursor
from src.utils.mq import publish_job
import json

def main():
    with get_db_cursor() as cur:
        # Reset stuck jobs (running for more than 2 hours)
        cur.execute("""
            UPDATE jobs 
            SET status = 'pending' 
            WHERE status = 'running' 
            AND started_at < NOW() - INTERVAL '2 hours'
        """)
        
        cur.execute("SELECT job_id, params FROM jobs WHERE status = 'pending'")
        rows = cur.fetchall()
        
        for row in rows:
            params = row['params']
            if isinstance(params, str):
                params = json.loads(params)
            
            # Ensure job_id is in params for handle_job to work
            params['job_id'] = row['job_id']
            
            publish_job(params)
            print(f"Republished Job {row['job_id']}: {params.get('stock_name')}")

if __name__ == "__main__":
    main()
