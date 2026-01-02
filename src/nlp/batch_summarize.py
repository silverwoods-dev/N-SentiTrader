import logging
import json
from src.db.connection import get_db_cursor
from src.nlp.summarizer import NewsSummarizer
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def batch_summarize(stock_code=None, limit=100):
    """
    아직 요약되지 않은 뉴스를 찾아 BERT 기반으로 요약을 생성하고 저장합니다.
    """
    summarizer = NewsSummarizer()
    
    with get_db_cursor() as cur:
        if stock_code:
            logger.info(f"Fetching news for {stock_code} (Limit: {limit})...")
            cur.execute("""
                SELECT c.url_hash, c.content 
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s AND c.extracted_content IS NULL
                LIMIT %s
            """, (stock_code, limit))
        else:
            logger.info(f"Fetching news for ALL stocks (Limit: {limit})...")
            cur.execute("""
                SELECT url_hash, content FROM tb_news_content 
                WHERE extracted_content IS NULL
                LIMIT %s
            """, (limit,))
            
        rows = cur.fetchall()
        
    if not rows:
        logger.info("No news found to summarize.")
        return

    logger.info(f"Summarizing {len(rows)} news articles...")
    
    success_count = 0
    for row in tqdm(rows):
        url_hash = row['url_hash']
        content = row['content']
        
        if not content or len(content) < 100:
            continue
            
        try:
            summary = summarizer.summarize(content, top_k=3)
            
            with get_db_cursor() as cur:
                cur.execute("""
                    UPDATE tb_news_content 
                    SET extracted_content = %s 
                    WHERE url_hash = %s
                """, (summary, url_hash))
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to summarize {url_hash}: {e}")

    logger.info(f"Successfully summarized {success_count}/{len(rows)} articles.")

if __name__ == "__main__":
    import sys
    stock = sys.argv[1] if len(sys.argv) > 1 else None
    batch_summarize(stock_code=stock)
