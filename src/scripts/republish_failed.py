# src/scripts/republish_failed.py
from src.db.connection import get_db_cursor
from src.utils.mq import publish_url

def main():
    with get_db_cursor() as cur:
        cur.execute("SELECT url, url_hash FROM tb_news_url WHERE status = 'failed'")
        rows = cur.fetchall()
        
        for row in rows:
            # We don't have stock_code in tb_news_url, but we can infer it for this test
            # or just publish without it (BodyCollector will just skip mapping if missing)
            # But for Samsung test, we want the mapping.
            publish_url({"url": row['url'], "url_hash": row['url_hash'], "stock_code": "005930"})
            cur.execute("UPDATE tb_news_url SET status = 'pending' WHERE url_hash = %s", (row['url_hash'],))
            print(f"Republished: {row['url']}")

if __name__ == "__main__":
    main()
