import json
import sys
from src.db.connection import get_db_cursor
from src.utils.mq import publish_verification_job

def trigger(stock_code):
    # 1. Insert Job
    with get_db_cursor() as cur:
        params = {"val_months": 1}
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, params, status)
            VALUES (%s, 'AWO_SCAN', %s, 'running')
            RETURNING v_job_id
        """, (stock_code, json.dumps(params)))
        v_job_id = cur.fetchone()['v_job_id']
        print(f"Created Job {v_job_id}")

    # 2. Publish
    payload = {
        "v_type": "AWO_SCAN",
        "stock_code": stock_code,
        "v_job_id": v_job_id,
        "val_months": 1
    }
    publish_verification_job(payload)
    print(f"Published Job {v_job_id}")

if __name__ == "__main__":
    stock = sys.argv[1] if len(sys.argv) > 1 else "005930"
    trigger(stock)
