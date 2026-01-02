import polars as pl
from src.learner.tech_indicators import TechIndicatorProvider
from src.db.connection import get_db_cursor
from datetime import datetime, timedelta

def test_tech_indicators():
    stock_code = "005930"
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=100)
    
    with get_db_cursor() as cur:
        df = TechIndicatorProvider.fetch_and_calculate(cur, stock_code, start_date, end_date)
        
    if df.is_empty():
        print("No data found for 005930")
        return
        
    print(f"Columns: {df.columns}")
    print(df.tail(5))
    
    # Check if indicators are not all zero/null
    for col in ["tech_rsi_14", "tech_macd_line"]:
        val = df[col].tail(1)[0]
        print(f"{col}: {val}")

if __name__ == "__main__":
    test_tech_indicators()
