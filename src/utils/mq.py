# src/utils/mq.py
import os
import pika
import json

MQ_HOST = os.getenv("MQ_HOST", "localhost")
MQ_USER = os.getenv("MQ_USER", "guest")
MQ_PASS = os.getenv("MQ_PASS", "guest")
QUEUE_NAME = "news_urls"
JOB_QUEUE_NAME = "address_jobs"

DLX_NAME = "nsenti.dlx"
DLQ_NAME = "dead_letter_queue"

def setup_dlx(channel):
    """Declare DLX and DLQ, then bind them."""
    channel.exchange_declare(exchange=DLX_NAME, exchange_type='direct')
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    # Note: We bind all default queues to this DLQ via their name as routing key
    # or we can use a catch-all. For simplicity, we'll bind common ones.
    for q in [QUEUE_NAME, JOB_QUEUE_NAME]:
        channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key=q)

def get_mq_channel(queue_name=QUEUE_NAME):
    credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=MQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    
    # Setup DLX if not already done (idempotent)
    setup_dlx(channel)
    
    # Declare Primary Queue with DLX
    channel.queue_declare(
        queue=queue_name, 
        durable=True,
        arguments={
            'x-dead-letter-exchange': DLX_NAME,
            'x-dead-letter-routing-key': queue_name
        }
    )
    return connection, channel

def publish_url(url_data):
    connection, channel = get_mq_channel(QUEUE_NAME)
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(url_data),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
        )
    )
    connection.close()

def publish_job(job_data):
    connection, channel = get_mq_channel(JOB_QUEUE_NAME)
    channel.basic_publish(
        exchange='',
        routing_key=JOB_QUEUE_NAME,
        body=json.dumps(job_data),
        properties=pika.BasicProperties(
            delivery_mode=2,
        )
    )
    connection.close()

def get_active_worker_count():
    import requests
    try:
        url = f"http://{MQ_HOST}:15672/api/overview"
        response = requests.get(url, auth=(MQ_USER, MQ_PASS), timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get('object_totals', {}).get('consumers', 0)
    except Exception as e:
        print(f"Error fetching RabbitMQ worker count: {e}")
    return 0

def get_queue_depths():
    import requests
    try:
        url = f"http://{MQ_HOST}:15672/api/queues"
        response = requests.get(url, auth=(MQ_USER, MQ_PASS), timeout=2)
        if response.status_code == 200:
            data = response.json()
            return {q['name']: q.get('messages', 0) for q in data}
    except Exception as e:
        print(f"Error fetching RabbitMQ queue depths: {e}")
    return {}
