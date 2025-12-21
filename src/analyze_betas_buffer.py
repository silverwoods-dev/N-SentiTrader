from src.db.connection import get_db_cursor
import pandas as pd

def analyze_betas_buffer():
    with get_db_cursor() as cur:
        cur.execute("SELECT word, beta FROM tb_sentiment_dict WHERE stock_code = '005930' AND source = 'Buffer'")
        rows = cur.fetchall()
        
    if not rows:
        print("No buffer data found for 005930")
        return

    df = pl_df = pd.DataFrame(rows)
    df['beta'] = df['beta'].astype(float)
    
    pos = df[df['beta'] > 0]
    neg = df[df['beta'] < 0]
    
    print("--- Buffer Positive Beta Stats ---")
    print(pos['beta'].describe())
    
    print("\n--- Buffer Negative Beta Stats ---")
    print(neg['beta'].describe())
    
    print(f"\nTotal: {len(df)}")
    print(f"Positive: {len(pos)}, Negative: {len(neg)}")

if __name__ == "__main__":
    analyze_betas_buffer()
