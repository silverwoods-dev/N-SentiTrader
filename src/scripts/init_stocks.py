# src/scripts/init_stocks.py
from src.db.connection import get_db_cursor

def main():
    stocks = [
        ("005930", "삼성전자", "KOSPI"),
        ("000660", "SK하이닉스", "KOSPI"),
        # Add more if needed
    ]
    
    with get_db_cursor() as cur:
        for code, name, market in stocks:
            cur.execute(
                """INSERT INTO tb_stock_master (stock_code, stock_name, market_type) 
                   VALUES (%s, %s, %s) ON CONFLICT (stock_code) DO NOTHING""",
                (code, name, market)
            )
    print("Stocks initialized.")

if __name__ == "__main__":
    main()
