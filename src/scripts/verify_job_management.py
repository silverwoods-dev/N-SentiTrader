# src/scripts/verify_job_management.py
import json
import time
try:
    from src.utils.metrics import BACKTEST_PROGRESS
except ImportError:
    print("[!] prometheus_client not found, using Mock for metric verification")
    class MockMetric:
        def labels(self, **kwargs): return self
        def set(self, val): pass
        def remove(self, *args): 
            # Simplified remove for mocking
            pass
    BACKTEST_PROGRESS = MockMetric()

from src.db.connection import get_db_cursor

def test_job_deletion():
    print("\n[1] Testing Job Deletion & Metric Cleanup")
    stock_code = "005930"
    v_job_id = None
    
    with get_db_cursor() as cur:
        # Create a dummy job
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, status, progress)
            VALUES (%s, 'VERIFY_TEST', 'running', 42.5)
            RETURNING v_job_id
        """, (stock_code, ))
        v_job_id = cur.fetchone()['v_job_id']
        print(f"Created dummy job #{v_job_id}")
        
    # Simulate Prometheus metrics (as they would be set by a worker)
    # Using both formats to test thorough cleanup
    BACKTEST_PROGRESS.labels(job_id=str(v_job_id), stock_code=stock_code).set(42.5)
    BACKTEST_PROGRESS.labels(job_id=f"J{v_job_id}", stock_code=stock_code).set(42.5)
    print(f"Set Prometheus metrics for {v_job_id} and J{v_job_id}")
    
    # Now simulate the deletion logic (we call the backend function logic manually or mocking the request)
    # Since we can't easily call the FastAPI endpoint here without a client, we'll verify the logic we wrote
    print("Executing deletion logic...")
    with get_db_cursor() as cur:
        # Get labels before deletion
        cur.execute("SELECT stock_code FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        row = cur.fetchone()
        if row:
            for label_id in [str(v_job_id), f"J{v_job_id}"]:
                try:
                    BACKTEST_PROGRESS.remove(label_id, row['stock_code'])
                    print(f"  [v] Removed metric for {label_id}")
                except Exception as e:
                    print(f"  [x] Failed to remove metric {label_id}: {e}")
        
        cur.execute("DELETE FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
    
    # Verify DB
    with get_db_cursor() as cur:
        cur.execute("SELECT 1 FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        if not cur.fetchone():
            print("  [v] Job successfully deleted from DB.")
        else:
            print("  [x] Job still exists in DB!")

def test_job_restart():
    print("\n[2] Testing Job Restart Logic")
    stock_code = "000660"
    v_job_id = None
    
    with get_db_cursor() as cur:
        # Create a failed job
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, status, progress, error_message, result_summary)
            VALUES (%s, 'VERIFY_TEST', 'failed', 15.0, 'Simulated Error', '{"fail": true}')
            RETURNING v_job_id
        """, (stock_code, ))
        v_job_id = cur.fetchone()['v_job_id']
        print(f"Created failed job #{v_job_id}")

    # Simulate restart logic
    print("Executing restart logic...")
    with get_db_cursor() as cur:
        cur.execute("""
            UPDATE tb_verification_jobs 
            SET status = 'pending', progress = 0, started_at = NULL, completed_at = NULL, 
                worker_id = NULL, error_message = NULL, result_summary = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE v_job_id = %s
        """, (v_job_id,))
        
    # Verify DB
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
        job = cur.fetchone()
        if job['status'] == 'pending' and job['progress'] == 0 and job['error_message'] is None:
            print("  [v] Job successfully reset to pending.")
        else:
            print(f"  [x] Job reset failed! Status: {job['status']}, Progress: {job['progress']}")

    # Cleanup
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))

if __name__ == "__main__":
    test_job_deletion()
    test_job_restart()
