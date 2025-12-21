# src/scripts/backfill_news_dates.py
from src.collector.news import AddressCollector
from datetime import datetime, timedelta
import time

def main():
    collector = AddressCollector()
    stock_code = "005930"
    stock_name = "삼성전자"
    
    # 180일 수집 실행하여 published_at_hint 업데이트
    end_date = datetime(2025, 12, 17)
    target_days = 180
    
    print(f"\n>>> Starting date backfill for {target_days} days")
    for i in range(target_days):
        target_date = end_date - timedelta(days=i)
        ds = target_date.strftime("%Y.%m.%d")
        de = ds
        
        print(f"Processing Date: {ds}")
        collector.collect_by_range(stock_code, ds, de, query=stock_name)
        time.sleep(1) # 일자별 요청 사이 간격
        
    print(f"\n>>> Date backfill completed.")

if __name__ == "__main__":
    main()
