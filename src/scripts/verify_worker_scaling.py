# src/scripts/verify_worker_scaling.py
import json
import os
from src.utils.mq import get_mq_channel, VERIFICATION_QUEUE_NAME, VERIFICATION_DAILY_QUEUE_NAME, publish_verification_job

def test_routing():
    print("\n[1] Testing Verification Job Routing")
    
    # Job 1: Daily Update (Should go to verification_daily)
    daily_job = {"v_type": "DAILY_UPDATE", "stock_code": "005930", "v_job_id": 9991}
    # Job 2: AWO Scan (Should go to verification_jobs)
    heavy_job = {"v_type": "AWO_SCAN", "stock_code": "000660", "v_job_id": 9992}
    
    print("Publishing DAILY_UPDATE job...")
    publish_verification_job(daily_job)
    
    print("Publishing AWO_SCAN job...")
    publish_verification_job(heavy_job)
    
    # Check queues for messages
    print("\nVerifying queue depths (requires RabbitMQ API access or manual check)...")
    try:
        from src.utils.mq import get_queue_depths
        depths = get_queue_depths()
        
        print("\nAll Queues Found:")
        for name, data in depths.items():
            print(f"  - {name}: {data['total']} messages")
        
        daily_depth = depths.get(VERIFICATION_DAILY_QUEUE_NAME, {}).get("total", 0)
        heavy_depth = depths.get(VERIFICATION_QUEUE_NAME, {}).get("total", 0)
        
        print(f"  {VERIFICATION_DAILY_QUEUE_NAME} depth: {daily_depth}")
        print(f"  {VERIFICATION_QUEUE_NAME} depth: {heavy_depth}")
        
        if daily_depth > 0:
            print("  [v] DAILY_UPDATE routed to light queue.")
        if heavy_depth > 0:
            print("  [v] AWO_SCAN routed to heavy queue.")
            
    except Exception as e:
        print(f"  [!] Could not verify queue depths via API: {e}")
        print("  [Note] Manually check RabbitMQ Management UI at http://localhost:15672")

def test_worker_env_vars():
    print("\n[2] Testing Worker Environment Configuration")
    # This just checks if the script can read the vars as intended
    os.environ["MQ_QUEUE"] = "test_queue"
    os.environ["METRICS_PORT"] = "9999"
    
    # We would need to mock main() or similar, but let's just confirm imports work
    try:
        from src.scripts.run_verification_worker import VerificationWorker
        print("  [v] VerificationWorker class imported and ready for specialized tasks.")
    except Exception as e:
        print(f"  [x] Import failed: {e}")

if __name__ == "__main__":
    test_routing()
    test_worker_env_vars()
