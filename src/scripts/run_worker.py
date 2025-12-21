# src/scripts/run_worker.py
from src.collector.news import BodyCollector
from src.utils.mq import get_mq_channel, QUEUE_NAME
from src.utils.metrics import start_metrics_server
import time

def main():
    print("Starting BodyCollector Worker...")
    start_metrics_server() # Start Prometheus Metrics Exporter
    body_collector = BodyCollector()
    
    while True:
        try:
            connection, channel = get_mq_channel()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=body_collector.handle_message)
            
            print(f"Worker waiting for messages in {QUEUE_NAME}. To exit press CTRL+C")
            channel.start_consuming()
        except Exception as e:
            print(f"Worker connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    main()
