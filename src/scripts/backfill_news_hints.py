
import os
import sys

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

from src.db.connection import get_db_cursor

def backfill_hints():
    print("[*] Starting Backfill for News Hints...")
    
    with get_db_cursor() as cur:
        # 1. Count target rows
        cur.execute("""
            SELECT COUNT(*) 
            FROM tb_news_url u
            JOIN tb_news_content c ON u.url_hash = c.url_hash
            WHERE u.published_at_hint IS NULL AND c.published_at IS NOT NULL
        """)
        count = cur.fetchone()['count']
        print(f"[*] Found {count} rows to update.")
        
        if count == 0:
            print("[v] No backfill needed.")
            return

        # 2. Perform Update
        # Using a single efficient UPDATE with JOIN
        cur.execute("""
            UPDATE tb_news_url u
            SET published_at_hint = c.published_at::date
            FROM tb_news_content c
            WHERE u.url_hash = c.url_hash 
              AND u.published_at_hint IS NULL 
              AND c.published_at IS NOT NULL
        """)
        updated = cur.rowcount
        print(f"[v] Successfully updated {updated} rows.")

if __name__ == "__main__":
    backfill_hints()
