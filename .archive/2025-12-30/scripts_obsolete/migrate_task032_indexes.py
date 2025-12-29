"""
마이그레이션 스크립트: TASK-032 인덱스 추가

Timeline View 성능 최적화를 위한 인덱스 생성
"""

from src.db.connection import get_db_cursor

def migrate():
    """인덱스 추가 마이그레이션"""
    with get_db_cursor() as cur:
        print("Creating index: idx_sentiment_dict_updated_at...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_dict_updated_at 
            ON tb_sentiment_dict(stock_code, source, updated_at DESC)
        """)
        
        print("Creating index: idx_sentiment_dict_word_version...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sentiment_dict_word_version
            ON tb_sentiment_dict(word, version, source)
        """)
        
        print("✅ Migration completed successfully!")

if __name__ == "__main__":
    migrate()
