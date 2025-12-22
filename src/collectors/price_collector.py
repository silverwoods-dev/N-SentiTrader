
import pandas as pd
from pykrx import stock
from src.db.connection import get_db_cursor
from datetime import datetime, timedelta
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PriceCollector:
    def __init__(self, benchmark_code="KOSPI"):
        self.benchmark_code = benchmark_code

    def collect_and_settle(self, stock_code: str, date_str: str = None):
        """
        Collect price for a specific date and update tb_predictions.actual_alpha.
        date_str: 'YYYYMMDD' (defaults to today)
        """
        if date_str is None:
            date_str = datetime.now().strftime('%Y%m%d')
        
        target_date = datetime.strptime(date_str, '%Y%m%d').date()
        logger.info(f"Settling alpha for {stock_code} on {target_date}")

        try:
            # 1. Fetch Stock Price (Today and Yesterday to get return)
            # We need at least 2 days of data to calculate return
            start_date = (target_date - timedelta(days=5)).strftime('%Y%m%d')
            end_date = date_str
            
            df_stock = stock.get_market_ohlcv_by_date(fromdate=start_date, todate=end_date, ticker=stock_code)
            if df_stock.empty:
                logger.warning(f"No stock price data for {stock_code} on {target_date}")
                return
            
            # 2. Fetch Benchmark (KOSPI)
            df_bm = stock.get_index_ohlcv_by_date(fromdate=start_date, todate=end_date, ticker="1001") # 1001 is KOSPI
            if df_bm.empty:
                # Try KOSDAQ if KOSPI fails or check if index code is correct
                # 1001 is KOSPI Composite
                logger.warning(f"No benchmark data for KOSPI on {target_date}")
                return

            # Note: Pykrx returns results with DatetimeIndex (Timestamp objects)
            target_ts = pd.Timestamp(target_date)
            
            if target_ts not in df_stock.index or target_ts not in df_bm.index:
                logger.warning(f"Target date {target_date} not yet available in market data.")
                return

            # Calculate returns for the target date
            # return = (close / prev_close) - 1
            # We use '등락률' if available, but let's be explicit.
            
            # Find integer index for target_date
            idx_stock = df_stock.index.get_loc(target_ts)
            idx_bm = df_bm.index.get_loc(target_ts)
            
            if idx_stock == 0 or idx_bm == 0:
                logger.warning("Insufficient history to calculate return rate.")
                return
                
            stock_close = float(df_stock.iloc[idx_stock]['종가'])
            stock_prev = float(df_stock.iloc[idx_stock-1]['종가'])
            stock_return = (stock_close / stock_prev) - 1
            stock_volume = int(df_stock.iloc[idx_stock]['거래량'])
            
            bm_close = float(df_bm.iloc[idx_bm]['종가'])
            bm_prev = float(df_bm.iloc[idx_bm-1]['종가'])
            bm_return = (bm_close / bm_prev) - 1
            
            # 3. Fetch Sector Return
            sector_return = 0.0
            with get_db_cursor() as cur:
                cur.execute("SELECT sector_code FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
                row = cur.fetchone()
                sector_code = row['sector_code'] if row else None
            
            if sector_code:
                from src.utils.sector_manager import SectorManager
                sector_return = SectorManager.get_sector_return(sector_code, target_date)
            
            excess_return = stock_return - bm_return
            
            logger.info(f"[{stock_code}] {target_date} - Stock Ret: {stock_return:.4f}, Vol: {stock_volume}, Alpha: {excess_return:.4f}, Sector Ret: {sector_return:.4f}")

            # 4. Save to tb_daily_price
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO tb_daily_price (date, stock_code, close_price, return_rate, excess_return, volume, sector_return)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date, stock_code) DO UPDATE SET
                    close_price = EXCLUDED.close_price,
                    return_rate = EXCLUDED.return_rate,
                    excess_return = EXCLUDED.excess_return,
                    volume = EXCLUDED.volume,
                    sector_return = EXCLUDED.sector_return
                """, (target_date, stock_code, stock_close, stock_return, excess_return, stock_volume, sector_return))
                
                # 5. Settle tb_predictions
                # Prediction with prediction_date = target_date means it was predicting for target_date.
                cur.execute("""
                    UPDATE tb_predictions
                    SET actual_alpha = %s,
                        is_correct = CASE WHEN (expected_alpha > 0 AND %s > 0) OR (expected_alpha < 0 AND %s < 0) THEN true ELSE false END
                    WHERE stock_code = %s AND prediction_date = %s
                """, (excess_return, excess_return, excess_return, stock_code, target_date))
                
                rows_updated = cur.rowcount
                logger.info(f"Settled {rows_updated} predictions for {stock_code} on {target_date}")

        except Exception as e:
            logger.error(f"Error in PriceCollector for {stock_code}: {e}")

if __name__ == "__main__":
    collector = PriceCollector()
    # Test for Samsung Electronics
    collector.collect_and_settle("005930", "20251219")
