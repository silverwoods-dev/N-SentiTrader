# src/scripts/run_address_worker.py
from src.collector.news import AddressCollector
from src.utils.mq import get_mq_channel, JOB_QUEUE_NAME
from src.utils.metrics import start_metrics_server
import time

def main():
    print("Starting AddressCollector Worker (Producer)...")
    start_metrics_server() # Start Prometheus Metrics Exporter
    collector = AddressCollector()
    
    while True:
        try:
            connection, channel = get_mq_channel(JOB_QUEUE_NAME)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=JOB_QUEUE_NAME, on_message_callback=collector.handle_job)
            
            print(f"Address Worker waiting for jobs in {JOB_QUEUE_NAME}. To exit press CTRL+C")
            channel.start_consuming()
        except Exception as e:
            print(f"Address Worker connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
