
import json
from src.utils.mq import publish_verification_job
from src.db.connection import get_db_cursor
import logging

logging.basicConfig(level=logging.INFO)

def requeue_72():
    v_job_id = 72
    print(f"Manually requeueing Job #{v_job_id}...")
    
    with get_db_cursor() as cur:
        cur.execute("SELECT stock_code, v_type, params FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        row = cur.fetchone()
        if row:
            params = row['params']
            if isinstance(params, str):
                params = json.loads(params)
            
            payload = {
                "v_job_id": v_job_id,
                "v_type": row['v_type'],
                "stock_code": row['stock_code'],
                "val_months": params.get("val_months", 1)
            }
            print(f"Payload: {payload}")
            publish_verification_job(payload)
            print("Successfully published to MQ.")
        else:
            print("Job not found in DB.")

if __name__ == "__main__":
    requeue_72()
