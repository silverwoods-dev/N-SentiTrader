import os
import sys
import logging
import json
from datetime import datetime, timedelta

# Project Root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from src.db.connection import get_db_cursor
from src.nlp.summarizer import NewsSummarizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_bulk_summarization(stock_code='005930', years=2):
    """
    특정 종목의 최근 N년치 뉴스 중 요약이 없는 데이터를 찾아 일괄 요약 수행
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * years)
    
    logger.info(f"[*] Starting Bulk Summarization for {stock_code} ({years} years)")
    logger.info(f"[*] Period: {start_date.date()} ~ {end_date.date()}")

    # 1. 대상 뉴스 조회 (요약이 없는 것만)
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT c.url_hash, c.content
            FROM tb_news_content c
            JOIN tb_news_mapping m ON c.url_hash = m.url_hash
            WHERE m.stock_code = %s 
            AND c.published_at BETWEEN %s AND %s
            AND c.extracted_content IS NULL
            AND c.content IS NOT NULL
        """, (stock_code, start_date, end_date))
        target_news = cur.fetchall()

    total = len(target_news)
    if total == 0:
        logger.info("[*] No missing summaries found for the given period.")
        return

    logger.info(f"[*] Found {total} news items missing summaries.")

    # 2. 일괄 요약 수행 (64개씩 끊어서 처리)
    batch_size = 64
    for i in range(0, total, batch_size):
        batch = target_news[i:i + batch_size]
        logger.info(f"[*] Processing batch {i//batch_size + 1} / {total//batch_size + 1} ({i}/{total})")
        
        # NewsSummarizer.bulk_ensure_summaries는 내부적으로 DB UPDATE를 수행함
        # 리스트 내 딕셔너리에 'url_hash', 'content'가 있어야 함
        NewsSummarizer.bulk_ensure_summaries(batch)
        
        # 주기적인 GC
        if i % 256 == 0:
            import gc
            gc.collect()

    logger.info(f"[*] Bulk Summarization Completed for {stock_code}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock", type=str, default="005930", help="Stock code")
    parser.add_argument("--years", type=int, default=2, help="Number of years back")
    args = parser.parse_args()
    
    run_bulk_summarization(stock_code=args.stock, years=args.years)
