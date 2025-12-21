import FinanceDataReader as fdr
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor

def collect_stock_data(stock_code, start_date, end_date):
    """
    FinanceDataReader를 사용하여 주가 데이터를 수집하고 DB에 저장합니다.
    """
    print(f"Collecting stock data for {stock_code} from {start_date} to {end_date}...")
    
    # 주가 데이터 가져오기
    df = fdr.DataReader(stock_code, start_date, end_date)
    
    # 시장 지수(KOSPI) 데이터 가져오기 (초과 수익률 계산용)
    df_kospi = fdr.DataReader('KS11', start_date, end_date)
    
    with get_db_cursor() as cur:
        # 종목 마스터 확인 및 등록
        cur.execute("SELECT 1 FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO tb_stock_master (stock_code, stock_name, market_type) VALUES (%s, %s, %s)",
                (stock_code, "삼성전자", "KOSPI")
            )

        for date, row in df.iterrows():
            date_str = date.strftime('%Y-%m-%d')
            close_price = float(row['Close'])
            
            # 등락률 계산 (전일 종가 대비)
            # FDR 데이터에는 'Change' 컬럼이 포함되어 있음
            return_rate = float(row['Change'])
            
            # KOSPI 등락률 가져오기
            kospi_change = 0.0
            if date in df_kospi.index:
                kospi_change = float(df_kospi.loc[date]['Change'])
            
            # 초과 수익률 = 종목 등락률 - 시장 등락률
            excess_return = return_rate - kospi_change
            
            cur.execute("""
                INSERT INTO tb_daily_price (date, stock_code, close_price, return_rate, excess_return)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (date, stock_code) DO UPDATE SET
                close_price = EXCLUDED.close_price,
                return_rate = EXCLUDED.return_rate,
                excess_return = EXCLUDED.excess_return
            """, (date_str, stock_code, close_price, return_rate, excess_return))
            
    print(f"Successfully saved {len(df)} days of stock data.")

if __name__ == "__main__":
    # 테스트를 위해 최근 1년치 데이터 수집
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    collect_stock_data("005930", start_date, end_date)
