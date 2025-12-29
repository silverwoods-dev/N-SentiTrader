
from src.db.connection import get_db_cursor
from datetime import timedelta

def check_news():
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT title, published_at 
            FROM tb_news_content 
            ORDER BY published_at DESC LIMIT 5
        """)
        rows = cur.fetchall()
        for row in rows:
            pub_utc = row['published_at']
            pub_kst = pub_utc + timedelta(hours=9)
            print(f"Title: {row['title'][:30]}...")
            print(f"  UTC: {pub_utc}")
            print(f"  KST: {pub_kst}")

if __name__ == "__main__":
    check_news()
