# src/scripts/sync_news_dates.py
from src.db.connection import get_db_cursor

def main():
    with get_db_cursor() as cur:
        print("Syncing published_at from hint...")
        cur.execute("""
            UPDATE tb_news_content c
            SET published_at = u.published_at_hint
            FROM tb_news_url u
            WHERE c.url_hash = u.url_hash
            AND c.published_at IS NULL
            AND u.published_at_hint IS NOT NULL
        """)
        print(f"Updated {cur.rowcount} rows.")

if __name__ == "__main__":
    main()
