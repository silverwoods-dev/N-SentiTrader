# src/tools/manual_collect_prices.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.collectors.price_collector import PriceCollector

DATES = ["20251222", "20251223", "20251224", "20251226"]
STOCKS = ["005930", "000660"]

def main():
    collector = PriceCollector()
    print("="*60)
    print("  Manual Price Collection (Dec 22 ~ Dec 26)")
    print("="*60)
    
    for date_str in DATES:
        for stock in STOCKS:
            print(f"Collecting {stock} for {date_str}...")
            try:
                collector.collect_and_settle(stock, date_str)
            except Exception as e:
                print(f"  [Error] {e}")

if __name__ == "__main__":
    main()
