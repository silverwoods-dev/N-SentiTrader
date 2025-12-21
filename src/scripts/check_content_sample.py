from src.db.connection import get_db_cursor

def check_content_sample():
    with get_db_cursor() as cur:
        # tb_news_content에는 created_at이 없으므로 tb_news_url과 조인하여 확인
        cur.execute("""
            SELECT c.title, c.content, c.published_at 
            FROM tb_news_content c
            JOIN tb_news_url u ON c.url_hash = u.url_hash
            ORDER BY u.created_at DESC 
            LIMIT 10 OFFSET 20
        """)
        rows = cur.fetchall()
        if not rows:
            print("No data found in the middle range.")
            return
            
        for i, row in enumerate(rows):
            print(f"--- Sample {i+1} (Middle Range) ---")
            print(f"Title: {row['title']}")
            # 본문이 길 수 있으므로 앞부분 150자만 출력
            content_preview = row['content'].replace('\n', ' ')[:150]
            print(f"Content: {content_preview}...")
            print(f"Published At: {row['published_at']}")
            print("-" * 30)

if __name__ == "__main__":
    check_content_sample()
