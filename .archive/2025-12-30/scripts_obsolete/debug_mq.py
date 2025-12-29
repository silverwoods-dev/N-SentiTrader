import requests
import os
import json

MQ_HOST = os.getenv("MQ_HOST", "localhost")
MQ_USER = os.getenv("MQ_USER", "guest")
MQ_PASS = os.getenv("MQ_PASS", "guest")
MQ_API_PORT = 15672

def check_queues():
    url = f"http://{MQ_HOST}:{MQ_API_PORT}/api/queues"
    try:
        resp = requests.get(url, auth=(MQ_USER, MQ_PASS))
        if resp.status_code == 200:
            queues = resp.json()
            print(f"{'Queue Name':<30} | {'Ready':<10} | {'Unacked':<10} | {'Consumers':<10}")
            print("-" * 70)
            for q in queues:
                print(f"{q['name']:<30} | {q.get('messages_ready',0):<10} | {q.get('messages_unacknowledged',0):<10} | {q.get('consumers',0):<10}")
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Connection Failed: {e}")

if __name__ == "__main__":
    check_queues()
