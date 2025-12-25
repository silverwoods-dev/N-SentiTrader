
import sys
import os
sys.path.append(os.getcwd())
from src.db.connection import get_db_cursor
import json

def check_db():
    with get_db_cursor() as cur:
        print("--- Table: tb_stock_fundamentals ---")
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'tb_stock_fundamentals' ORDER BY ordinal_position;")
        cols = cur.fetchall()
        for col in cols:
            print(f"{col['column_name']} ({col['data_type']})")
        
        print("\n--- Data Stats for 005930 (Samsung) ---")
        cur.execute("SELECT COUNT(*), MIN(base_date), MAX(base_date) FROM tb_stock_fundamentals WHERE stock_code = '005930';")
        stat = cur.fetchone()
        print(f"Fundamentals Count: {stat['count']}, Range: {stat['min']} ~ {stat['max']}")

        print("\n--- Price Stats for 005930 (Samsung) ---")
        cur.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM tb_daily_price WHERE stock_code = '005930';")
        pstat = cur.fetchone()
        print(f"Prices Count: {pstat['count']}, Range: {pstat['min']} ~ {pstat['max']}")

if __name__ == "__main__":
    try:
        check_db()
    except Exception as e:
        print(f"Error: {e}")
