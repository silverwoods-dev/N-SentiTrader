# src/scripts/run_address_worker.py
import os
import json
import time
import logging
import multiprocessing
import socket
from src.collector.news import AddressCollector
from src.utils.mq import get_mq_channel, JOB_QUEUE_NAME
from src.utils.metrics import start_metrics_server, BACKTEST_PROGRESS
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_job_process(data, queue_name):
    """Function to run news collection in a separate process."""
    collector = AddressCollector()
    # AddressCollector.handle_job takes (ch, method, properties, body)
    # But here we are calling it without MQ context for the purely heavy work
    # We might need to adjust handle_job in news.py or just call the core logic.
    # Actually, let's let handle_job handle its own DB transaction but NOT ack.
    collector.handle_job(None, None, None, json.dumps(data))

class AddressWorkerWrapper:
    def __init__(self, queue_name):
        self.queue_name = queue_name
        self.collector = AddressCollector()

    def handle_job_with_heartbeat(self, ch, method, properties, body):
        data = json.loads(body)
        job_id = data.get("job_id")
        stock_code = data.get("stock_code")
        
        logger.info(f"[*] Dispatching worker process for Job {job_id} in {self.queue_name}")
        
        # Start work in a separate process
        p = multiprocessing.Process(target=run_job_process, args=(data, self.queue_name))
        p.start()
        
        # Heartbeat loop
        counter = 0
        while p.is_alive():
            try:
                if ch.connection.is_open:
                    ch.connection.process_data_events(time_limit=1)
                else:
                    logger.warning(f"[!] connection lost during Job {job_id}")
                    break
                
                # Sync Metrics from DB every 5 seconds
                counter += 1
                if counter % 5 == 0:
                    try:
                        with get_db_cursor() as cur:
                            cur.execute("SELECT progress FROM jobs WHERE job_id = %s", (job_id,))
                            row = cur.fetchone()
                            if row and row['progress'] is not None:
                                # Prefix J is used for AddressWorker jobs to distinguish
                                BACKTEST_PROGRESS.labels(job_id=f"J{job_id}", stock_code=stock_code).set(row['progress'])
                    except Exception as me:
                        logger.error(f"Metric sync error: {me}")

            except Exception as e:
                logger.error(f"Error during heartbeat: {e}")
                break
            time.sleep(1)
            
        # Ack after process ends
        try:
            if ch.connection.is_open:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"[v] Completed and Acked Job {job_id}")
        except Exception as e:
            logger.error(f"Error acknowledging: {e}")

def main():
    start_metrics_server()
    queue_name = os.getenv("MQ_QUEUE", JOB_QUEUE_NAME)
    logger.info(f"Starting Address Worker on {queue_name} (Multiprocessing Enabled)...")
    
    wrapper = AddressWorkerWrapper(queue_name)
    
    while True:
        try:
            connection, channel = get_mq_channel(queue_name)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=wrapper.handle_job_with_heartbeat)
            
            logger.info(f"Waiting for jobs in {queue_name}...")
            channel.start_consuming()
        except Exception as e:
            logger.error(f"Connection error: {e}. Retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    main()
