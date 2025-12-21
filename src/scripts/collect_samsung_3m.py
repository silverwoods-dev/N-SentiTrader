# src/scripts/collect_samsung_3m.py
from src.collector.news import AddressCollector
from datetime import datetime, timedelta
import time

def collect_days(collector, stock_code, stock_name, days_count):
    end_date = datetime(2025, 12, 17) # 어제 날짜 고정
    
    print(f"\n--- Collecting {days_count} days for {stock_name} ---")
    for i in range(days_count):
        target_date = end_date - timedelta(days=i)
        ds = target_date.strftime("%Y.%m.%d")
        de = ds # 시작일과 종료일을 동일하게 설정하여 1일 단위 수집
        
        print(f"Target Date: {ds}")
        collector.collect_by_range(stock_code, ds, de, query=stock_name)
        time.sleep(2) # 일자별 요청 사이 간격

def main():
    collector = AddressCollector()
    stock_code = "005930"
    stock_name = "삼성전자"
    
    # 3개월(약 90일) 수집 실행
    target_days = 90
    print(f"\n>>> Starting sequential collection for {target_days} days")
    collect_days(collector, stock_code, stock_name, target_days)
    print(f"\n>>> Collection of {target_days} days completed.")

if __name__ == "__main__":
    main()
