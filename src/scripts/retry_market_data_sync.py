import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import get_db_cursor
from src.collectors.price_collector import PriceCollector
from src.collectors.fundamentals_collector import FundamentalsCollector
from datetime import datetime
import logging
import time

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RetrySync")

def get_missing_dates():
    """Find dates where news exists but price data is missing."""
    stocks = ['005930', '000660']
    missing_data = {}
    
    for stock_code in stocks:
        with get_db_cursor() as cur:
            # Get distinct dates where news exists
            cur.execute("""
                SELECT DISTINCT (c.published_at + interval '9 hours')::date as kst_date
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s AND c.published_at IS NOT NULL
                ORDER BY kst_date DESC
            """, (stock_code,))
            news_dates = {r['kst_date'] for r in cur.fetchall()}
            
            # Get dates where price data exists
            cur.execute("""
                SELECT DISTINCT date
                FROM tb_daily_price
                WHERE stock_code = %s
            """, (stock_code,))
            price_dates = {r['date'] for r in cur.fetchall()}
            
            # Find missing dates
            missing = news_dates - price_dates
            if missing:
                missing_data[stock_code] = sorted(missing, reverse=True)
                logger.info(f"{stock_code}: {len(missing)} dates missing price data")
    
    return missing_data

def retry_sync_with_throttle():
    """Retry collecting market data for missing dates with API throttling."""
    p_collector = PriceCollector()
    f_collector = FundamentalsCollector()
    
    missing_data = get_missing_dates()
    
    if not missing_data:
        logger.info("No missing data found. All synced!")
        return
    
    for stock_code, dates in missing_data.items():
        logger.info(f"=== Processing {stock_code}: {len(dates)} dates ===")
        
        # Collect fundamentals for the range
        if dates:
            start_date_str = min(dates).strftime('%Y%m%d')
            end_date_str = max(dates).strftime('%Y%m%d')
            logger.info(f"Fundamentals range: {start_date_str} ~ {end_date_str}")
            try:
                f_collector.collect(stock_code, start_date_str, end_date_str)
                time.sleep(3)  # Throttle between fundamentals calls
            except Exception as e:
                logger.error(f"Fundamentals collection failed: {e}")
        
        # Process each missing date with throttling
        count = 0
        for d in dates:
            ds = d.strftime('%Y%m%d')
            try:
                p_collector.collect_and_settle(stock_code, ds)
                count += 1
                if count % 10 == 0:
                    logger.info(f"Processed {count}/{len(dates)} dates for {stock_code}")
                    time.sleep(5)  # Extra pause every 10 requests
                else:
                    time.sleep(2)  # Standard throttle
            except Exception as e:
                logger.error(f"Failed to process {stock_code} on {ds}: {e}")
                if "429" in str(e) or "403" in str(e):
                    logger.warning("Rate limit hit. Waiting 60 seconds...")
                    time.sleep(60)

if __name__ == "__main__":
    retry_sync_with_throttle()
