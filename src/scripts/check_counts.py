from src.db.connection import get_db_cursor

def check_counts():
    with get_db_cursor() as cur:
        cur.execute("SELECT count(*) as cnt FROM tb_news_url")
        url_count = cur.fetchone()['cnt']
        
        cur.execute("SELECT count(*) as cnt FROM tb_news_url WHERE status = 'collected'")
        collected_count = cur.fetchone()['cnt']
        
        cur.execute("SELECT count(*) as cnt FROM tb_news_content")
        content_count = cur.fetchone()['cnt']
        
        print(f"Total URLs: {url_count}")
        print(f"Collected URLs: {collected_count}")
        print(f"Content items: {content_count}")

if __name__ == "__main__":
    check_counts()
