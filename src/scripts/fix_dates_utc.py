from src.db.connection import get_db_cursor

def migrate_dates():
    with get_db_cursor() as cur:
        print("Migrating missing dates from tb_news_url to tb_news_content (KST -> UTC)...")
        cur.execute("""
            UPDATE tb_news_content c
            SET published_at = (u.published_at_hint::timestamp - interval '9 hours')
            FROM tb_news_url u
            WHERE c.url_hash = u.url_hash 
              AND c.published_at IS NULL 
              AND u.published_at_hint IS NOT NULL;
        """)
        print(f"Updated {cur.rowcount} rows.")

if __name__ == "__main__":
    migrate_dates()
