from src.db.connection import get_db_cursor
import pandas as pd

def analyze_betas():
    with get_db_cursor() as cur:
        cur.execute("SELECT word, beta FROM tb_sentiment_dict WHERE stock_code = '005930'")
        rows = cur.fetchall()
        
    if not rows:
        print("No data found for 005930")
        return

    df = pd.DataFrame(rows)
    df['beta'] = df['beta'].astype(float)
    
    pos = df[df['beta'] > 0]
    neg = df[df['beta'] < 0]
    
    print("--- Positive Beta Stats ---")
    print(pos['beta'].describe())
    print("\nTop 5 Positive Words:")
    print(pos.sort_values('beta', ascending=False).head(5))
    
    print("\n--- Negative Beta Stats ---")
    print(neg['beta'].describe())
    print("\nTop 5 Negative Words:")
    print(neg.sort_values('beta', ascending=True).head(5))
    
    print(f"\nTotal Words: {len(df)}")
    print(f"Positive Count: {len(pos)}")
    print(f"Negative Count: {len(neg)}")

if __name__ == "__main__":
    analyze_betas()
