# src/utils/metrics.py
import os
from prometheus_client import start_http_server, Counter, Gauge, Histogram, Summary
import time

# Metrics definision
# Collector Metrics (Incremental)
COLLECTOR_URLS_TOTAL = Counter('nsenti_collector_urls_total', 'Total number of URLs discovered in session')
COLLECTOR_CONTENT_TOTAL = Counter('nsenti_collector_content_total', 'Total number of news content collected in session')
COLLECTOR_ERRORS_TOTAL = Counter('nsenti_collector_errors_total', 'Total number of collection errors', ['type'])

# Persistent Metrics (Database Snapshot)
NSENTI_TOTAL_URLS = Gauge('nsenti_total_urls', 'Total number of news URLs in database')
NSENTI_TOTAL_CONTENT = Gauge('nsenti_total_content', 'Total number of news content in database')
NSENTI_TOTAL_ERRORS = Gauge('nsenti_total_errors', 'Total number of news errors in database')

# Queue Metrics
QUEUE_DEPTH = Gauge('nsenti_queue_depth', 'Total number of messages in the queue (Ready + Unacked)', ['queue_name'])
QUEUE_MESSAGES_READY = Gauge('nsenti_queue_messages_ready', 'Number of messages ready to be delivered', ['queue_name'])
QUEUE_MESSAGES_UNACKED = Gauge('nsenti_queue_messages_unacked', 'Number of messages delivered to consumers but not yet acknowledged', ['queue_name'])

# Predictor Metrics
PREDICTIONS_TOTAL = Counter('nsenti_predictions_total', 'Total number of predictions made')
PREDICTION_LATENCY = Histogram('nsenti_prediction_seconds', 'Time taken to process prediction')

# Analysis Metrics
TRAINING_DURATION = Summary('nsenti_training_duration_seconds', 'Time taken for Lasso/Buffer dictionary training')

# Backtest Metrics
BACKTEST_JOBS_TOTAL = Counter('nsenti_backtest_jobs_total', 'Total number of backtest jobs created', ['stock_code', 'type'])
BACKTEST_JOBS_RUNNING = Gauge('nsenti_backtest_jobs_running', 'Number of currently running backtest jobs')
BACKTEST_JOBS_BY_STATUS = Gauge('nsenti_backtest_jobs_by_status', 'Number of backtest jobs by status', ['status'])
BACKTEST_PROGRESS = Gauge('nsenti_backtest_progress', 'Progress of backtest jobs', ['job_id', 'stock_code', 'job_type'])
BACKTEST_DURATION = Histogram('nsenti_backtest_duration_seconds', 'Time taken to complete backtest jobs', ['stock_code', 'type'])

def start_metrics_server(port=None):
    """
    Start Prometheus metrics server based on environment variable or provided port.
    """
    if port is None:
        port = int(os.getenv("METRICS_PORT", 9090))
    
    # Try current port and next 10 ports
    for p in range(port, port + 10):
        try:
            start_http_server(p)
            print(f"[*] Prometheus metrics server started on port {p}")
            return
        except OSError as e: # Address already in use
            if e.errno == 98 or "Address already in use" in str(e):
                print(f"[!] Port {p} in use, trying next...")
                continue
            else:
                print(f"[!] Failed to start metrics server on port {p}: {e}")
                return
        except Exception as e:
            print(f"[!] Failed to start metrics server on port {p}: {e}")
            pass
            
    print(f"[!] Failed to bind any metrics port starting from {port}")

if __name__ == "__main__":
    # Test
    start_metrics_server(9091)
    while True:
        COLLECTOR_URLS_TOTAL.inc()
        time.sleep(1)
