
from src.db.connection import get_db_cursor
from datetime import datetime, timedelta

def check_specific_news():
    with get_db_cursor() as cur:
        # Check the specific news about "반도체 핵심기술" that appears in screenshot
        cur.execute("""
            SELECT c.title, c.published_at, u.url
            FROM tb_news_content c
            JOIN tb_news_mapping m ON c.url_hash = m.url_hash
            JOIN tb_news_url u ON c.url_hash = u.url_hash
            WHERE m.stock_code = '000660'
              AND c.title LIKE '%반도체 핵심기술%'
            ORDER BY c.published_at DESC
            LIMIT 5
        """)
        rows = cur.fetchall()
        
        print("=== News matching '반도체 핵심기술' ===")
        for r in rows:
            pub_utc = r['published_at']
            pub_kst = pub_utc + timedelta(hours=9)
            print(f"\nTitle: {r['title'][:50]}...")
            print(f"  UTC: {pub_utc}")
            print(f"  KST: {pub_kst}")
            
            # Check if this should be included for 12-23 prediction
            target = datetime(2025, 12, 23).date()
            prev = datetime(2025, 12, 22).date()
            
            start_utc = datetime.combine(prev, datetime.min.time()) + timedelta(hours=7)
            end_utc = datetime.combine(target, datetime.min.time()) + timedelta(hours=7)
            
            included = start_utc <= pub_utc < end_utc
            print(f"  Should be in 12-23 evidence? {included}")
            print(f"  Window: {start_utc} to {end_utc}")

if __name__ == "__main__":
    check_specific_news()
