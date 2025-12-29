# src/scripts/run_verification_worker.py
import json
import time
import logging
import multiprocessing
from src.utils.mq import get_mq_channel, VERIFICATION_QUEUE_NAME
from src.utils.metrics import start_metrics_server, BACKTEST_PROGRESS
from src.learner.awo_engine import AWOEngine
from src.learner.manager import AnalysisManager
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_job_process(data):
    """Function to run in a separate process to avoid blocking heartbeats."""
    job_type = data.get("v_type")
    stock_code = data.get("stock_code")
    v_job_id = data.get("v_job_id")
    val_months = data.get("val_months", 1)

    logger.info(f"[Process] Starting {job_type} for {stock_code} (Job #{v_job_id})")
    try:
        if job_type == "AWO_SCAN":
            engine = AWOEngine(stock_code)
            engine.run_exhaustive_scan(validation_months=val_months, v_job_id=v_job_id)
            
        elif job_type == "AWO_SCAN_2D":
            engine = AWOEngine(stock_code)
            engine.run_exhaustive_scan(validation_months=val_months, v_job_id=v_job_id)
        
        elif job_type == "DAILY_UPDATE":
            am = AnalysisManager(stock_code)
            am.run_daily_update(v_job_id=v_job_id)
        
        elif job_type == "WF_CHECK":
            am = AnalysisManager(stock_code)
            am.run_walkforward_check(val_months=val_months, v_job_id=v_job_id)

        elif job_type == "FULL_PIPELINE":
            am = AnalysisManager(stock_code)
            am.run_full_pipeline(v_job_id=v_job_id)
            
        else:
            logger.error(f"Unknown verification job type: {job_type}")
            if v_job_id:
                from src.db.connection import get_db_cursor
                with get_db_cursor() as cur:
                    cur.execute(
                        "UPDATE tb_verification_jobs SET status = 'failed', error_message = %s, updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                        (f"Unknown job type: {job_type}", v_job_id)
                    )
            
    except Exception as e:
        logger.error(f"Error processing verification job in process: {e}")
        if v_job_id:
            from src.db.connection import get_db_cursor
            try:
                with get_db_cursor() as cur:
                    cur.execute(
                        "UPDATE tb_verification_jobs SET status = 'failed', error_message = %s, updated_at = CURRENT_TIMESTAMP WHERE v_job_id = %s",
                        (str(e), v_job_id)
                    )
            except Exception as db_e:
                logger.error(f"Failed to save error message to DB: {db_e}")

class VerificationWorker:
    def handle_job(self, ch, method, properties, body):
        data = json.loads(body)
        job_type = data.get("v_type")
        stock_code = data.get("stock_code")
        
        import socket
        hostname = socket.gethostname()
        v_job_id = data.get("v_job_id")
        
        # 1. Job Validation: Check if job exists and is still valid
        if v_job_id:
            from src.db.connection import get_db_cursor
            try:
                with get_db_cursor() as cur:
                    cur.execute(
                        "SELECT status FROM tb_verification_jobs WHERE v_job_id = %s",
                        (v_job_id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        logger.warning(f"[!] Abandoning Ghost Job #{v_job_id}: Not found in DB.")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
                    
                    if row['status'] in ['completed', 'failed', 'stopped']:
                        logger.warning(f"[!] Abandoning Job #{v_job_id}: Already in terminal state '{row['status']}'.")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
                        
                    # 2. Update DB with worker_id and status=running
                    # Setting status here prevents 'Zombie' alerts during MQ lag.
                    cur.execute(
                        "UPDATE tb_verification_jobs SET status = 'running', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, worker_id = %s WHERE v_job_id = %s",
                        (hostname, v_job_id)
                    )
            except Exception as e:
                logger.error(f"Failed to set status to running for job #{v_job_id}: {e}")
                # Optional: If DB error, maybe requeue? But for now, let's proceed to avoid blocking.
        else:
            logger.warning("[!] Received job without v_job_id. Proceeding with caution.")

        # Start the heavy task in a separate process
        p = multiprocessing.Process(target=run_job_process, args=(data,))
        p.start()
        
        # While the process is running, we must periodically process data events 
        # to keep the connection and heartbeats alive.
        counter = 0
        while p.is_alive():
            try:
                if ch.connection.is_open:
                    ch.connection.process_data_events(time_limit=1)
                else:
                    logger.warning(f"[!] RabbitMQ connection lost during Job #{v_job_id}. Process is still running.")
                    break # Cannot ack if connection is dead
                
                # Sync Metrics from DB every 5 seconds
                counter += 1
                if counter % 5 == 0:
                    try:
                        with get_db_cursor() as cur:
                            cur.execute("SELECT progress FROM tb_verification_jobs WHERE v_job_id = %s", (v_job_id,))
                            row = cur.fetchone()
                            if row and row['progress'] is not None:
                                BACKTEST_PROGRESS.labels(job_id=str(v_job_id), stock_code=stock_code).set(row['progress'])
                    except Exception as me:
                        logger.error(f"Metric sync error: {me}")

            except Exception as e:
                logger.error(f"Error during heartbeat process: {e}")
                break
            time.sleep(1)
            
        # Acknowledge the message once the process is done
        try:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(f"[v] Finished Verification Job: {job_type} for {stock_code}")
        except Exception as e:
            logger.error(f"Error acknowledging job: {e}")

def main():
    logger.info("Starting Verification Worker (Training/Backtest / Multiprocessing Enabled)...")
    start_metrics_server() 
    worker = VerificationWorker()
    
    while True:
        try:
            connection, channel = get_mq_channel(VERIFICATION_QUEUE_NAME)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=VERIFICATION_QUEUE_NAME, on_message_callback=worker.handle_job)
            
            logger.info(f"Verification Worker waiting for jobs in {VERIFICATION_QUEUE_NAME}. To exit press CTRL+C")
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Verification Worker connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
