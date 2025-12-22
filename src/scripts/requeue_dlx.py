# src/scripts/requeue_dlx.py
import json
import pika
from src.utils.mq import MQ_HOST, MQ_USER, MQ_PASS, DLQ_NAME

def requeue_all():
    credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=MQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    
    print(f"[*] Fetching messages from {DLQ_NAME}...")
    
    count = 0
    while True:
        method, properties, body = channel.basic_get(queue=DLQ_NAME, auto_ack=False)
        if method is None:
            break
            
        # Get original routing key from death headers
        death_headers = properties.headers.get('x-death', [])
        original_queue = None
        if death_headers:
            original_queue = death_headers[0].get('queue')
            
        if not original_queue:
            # Fallback (maybe it was pushed manually?)
            print(f"[!] Could not determine original queue for message. skipping...")
            channel.basic_ack(delivery_tag=method.delivery_tag)
            continue
            
        print(f"[*] Re-queuing message back to {original_queue}...")
        channel.basic_publish(
            exchange='',
            routing_key=original_queue,
            body=body,
            properties=pika.BasicProperties(delivery_mode=2)
        )
        channel.basic_ack(delivery_tag=method.delivery_tag)
        count += 1
        
    print(f"[v] Successfully re-queued {count} messages.")
    connection.close()

if __name__ == "__main__":
    requeue_all()
