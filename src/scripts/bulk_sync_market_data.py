
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.connection import get_db_cursor
from src.collectors.price_collector import PriceCollector
from src.collectors.fundamentals_collector import FundamentalsCollector
from datetime import datetime
import logging

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("BulkSync")

def run_bulk_sync():
    stocks = ['005930', '000660']
    p_collector = PriceCollector()
    f_collector = FundamentalsCollector()

    for stock_code in stocks:
        logger.info(f"=== Processing {stock_code} ===")
        with get_db_cursor() as cur:
            # Get distinct dates where news was published for this stock (KST)
            cur.execute("""
                SELECT DISTINCT (c.published_at + interval '9 hours')::date as kst_date
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s AND c.published_at IS NOT NULL
                ORDER BY kst_date DESC
            """, (stock_code,))
            rows = cur.fetchall()
            dates = [r['kst_date'] for r in rows]
            
            if not dates:
                logger.info(f"No news found for {stock_code}.")
                continue
                
            logger.info(f"Found {len(dates)} dates with news. Syncing market data...")
            
            # Fundamentals range
            start_date_str = min(dates).strftime('%Y%m%d')
            end_date_str = max(dates).strftime('%Y%m%d')
            logger.info(f"Fundamentals range: {start_date_str} ~ {end_date_str}")
            f_collector.collect(stock_code, start_date_str, end_date_str)
            
            # Price and Settle for each date
            count = 0
            for d in dates:
                ds = d.strftime('%Y%m%d')
                p_collector.collect_and_settle(stock_code, ds)
                count += 1
                if count % 10 == 0:
                    logger.info(f"Processed {count}/{len(dates)} dates for {stock_code}")

if __name__ == "__main__":
    run_bulk_sync()
