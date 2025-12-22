# tests/test_dlx.py
import os
import pika
import json
import time
import pytest
from src.utils.mq import MQ_HOST, MQ_USER, MQ_PASS, get_mq_channel

TEST_QUEUE = "test_dlx_primary"
DLX_NAME = "nsenti.dlx"
DLQ_NAME = "test_dlx_dead_letter"

def setup_dlx():
    credentials = pika.PlainCredentials(MQ_USER, MQ_PASS)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=MQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    
    # 1. Declare DLX
    channel.exchange_declare(exchange=DLX_NAME, exchange_type='direct')
    
    # 2. Declare DLQ
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key=TEST_QUEUE)
    
    # 3. Declare Primary Queue with DLX arguments
    channel.queue_declare(
        queue=TEST_QUEUE,
        durable=True,
        arguments={
            'x-dead-letter-exchange': DLX_NAME,
            'x-dead-letter-routing-key': TEST_QUEUE # Use original queue name as routing key for DLX
        }
    )
    return connection, channel

def test_message_moves_to_dlq():
    conn, ch = setup_dlx()
    
    # Clear queues
    ch.queue_purge(queue=TEST_QUEUE)
    ch.queue_purge(queue=DLQ_NAME)
    
    # Publish message to primary
    message = {"test": "dlx_data"}
    ch.basic_publish(
        exchange='',
        routing_key=TEST_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    
    # Consume and NACK (requeue=False)
    method, properties, body = ch.basic_get(queue=TEST_QUEUE, auto_ack=False)
    assert body is not None
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    
    # Wait a bit
    time.sleep(1)
    
    # Check DLQ
    method_dlx, props_dlx, body_dlx = ch.basic_get(queue=DLQ_NAME, auto_ack=True)
    assert body_dlx is not None
    assert json.loads(body_dlx) == message
    
    print("SUCCESS: Message moved to DLQ!")
    conn.close()

if __name__ == "__main__":
    test_message_moves_to_dlq()
