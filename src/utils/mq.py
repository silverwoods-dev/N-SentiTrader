# src/utils/mq.py
import os
import pika
import json

MQ_HOST = os.getenv("MQ_HOST", "localhost")
MQ_USER = os.getenv("MQ_USER", "guest")
MQ_PASS = os.getenv("MQ_PASS", "guest")
QUEUE_NAME = "news_urls"
JOB_QUEUE_NAME = "address_jobs"

def get_mq_channel(queue_name=QUEUE_NAME):
    credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=MQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
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
