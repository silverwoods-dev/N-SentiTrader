from src.collector.news import JobManager
import time

def main():
    manager = JobManager()
    stock_code = "005930"
    
    # Trigger remaining ranges to cover 2024.01.01 ~ present
    # Already running: 0-360
    ranges = [
        (90, 360),
        (90, 450),
        (90, 540),
        (90, 630)
    ]
    
    for days, offset in ranges:
        job_id = manager.create_backfill_job(stock_code, days, offset=offset)
        print(f"Triggered backfill: {days} days from offset {offset}. Job ID: {job_id}")
        time.sleep(1)

if __name__ == "__main__":
    main()
