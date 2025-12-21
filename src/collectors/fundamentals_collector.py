import pandas as pd
from pykrx import stock
from src.db.connection import get_db_cursor
from datetime import datetime
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FundamentalsCollector:
    def __init__(self):
        pass

    def collect(self, stock_code: str, start_date: str, end_date: str):
        """
        Collect fundamentals (PER, PBR, ROE, Cap) for a specific stock and date range.
        start_date, end_date: 'YYYYMMDD' or 'YYYY-MM-DD'
        """
        str_start = start_date.replace("-", "")
        str_end = end_date.replace("-", "")
        
        logger.info(f"Collecting fundamentals for {stock_code} from {str_start} to {str_end}")

        try:
            # 1. Fetch Fundamentals (PER, PBR, etc.)
            df_fund = stock.get_market_fundamental_by_date(fromdate=str_start, todate=str_end, ticker=stock_code)
            if df_fund.empty:
                logger.warning(f"No fundamental data for {stock_code}")
                return

            df_fund = df_fund.reset_index()
            # Expected columns: '날짜', 'BPS', 'PER', 'PBR', 'EPS', 'DIV', 'DPS'
            
            # 2. Fetch Market Cap
            time.sleep(1) # Respect rate limits
            df_cap = stock.get_market_cap_by_date(fromdate=str_start, todate=str_end, ticker=stock_code)
            df_cap = df_cap.reset_index()
            # Expected columns: '날짜', '시가총액', '거래량', '거래대금', '상장주식수'

            # 3. Merge
            # Some versions use 'Date' or '날짜'. check first column or merge on index if not reset
            date_col_fund = df_fund.columns[0] # Usually '날짜'
            date_col_cap = df_cap.columns[0]

            df_merged = pd.merge(df_fund, df_cap[[date_col_cap, '시가총액']], left_on=date_col_fund, right_on=date_col_cap, how='inner')
            
            with get_db_cursor() as cur:
                for _, row in df_merged.iterrows():
                    base_date = row[date_col_fund]
                    per = float(row['PER'])
                    pbr = float(row['PBR'])
                    
                    # ROE Calculation (Estimated as PBR/PER * 100 if PER != 0)
                    # OR EPS / BPS * 100
                    # Using provided columns
                    eps = float(row['EPS'])
                    bps = float(row['BPS'])
                    roe = 0.0
                    if bps > 0:
                        roe = (eps / bps) * 100
                    elif per > 0:
                        roe = (pbr / per) * 100
                    
                    market_cap = int(row['시가총액'])
                    
                    sql = """
                    INSERT INTO tb_stock_fundamentals (stock_code, base_date, per, pbr, roe, market_cap)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (stock_code, base_date) DO UPDATE SET
                    per = EXCLUDED.per, 
                    pbr = EXCLUDED.pbr, 
                    roe = EXCLUDED.roe, 
                    market_cap = EXCLUDED.market_cap;
                    """
                    cur.execute(sql, (stock_code, base_date, per, pbr, roe, market_cap))
            
            logger.info(f"Saved {len(df_merged)} rows for {stock_code}")

        except Exception as e:
            logger.error(f"Error collecting fundamentals for {stock_code}: {e}")

if __name__ == "__main__":
    # Test run
    collector = FundamentalsCollector()
    # Samsung Electronics
    collector.collect("005930", "20240101", "20240110")
