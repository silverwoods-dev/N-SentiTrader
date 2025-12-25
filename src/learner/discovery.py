
import polars as pl
import numpy as np
from src.db.connection import get_db_cursor
from src.nlp.tokenizer import Tokenizer
from src.utils.calendar import Calendar
from datetime import datetime, timedelta

class GlobalDiscoveryScanner:
    def __init__(self, horizon_days=365):
        self.horizon_days = horizon_days
        self.tokenizer = Tokenizer()

    def scan(self):
        print(f">>> [Global Discovery] Starting scan (Horizon: {self.horizon_days} days)...")
        start_date = (datetime.now() - timedelta(days=self.horizon_days)).strftime('%Y-%m-%d')
        
        # 1. Fetch News and returns across all active stocks
        # Optimization: Fetch only relevant columns
        with get_db_cursor() as cur:
            print("    Fetching joined news and return data...")
            cur.execute("""
                SELECT 
                    c.content, 
                    p.excess_return,
                    m.stock_code,
                    p.date
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                JOIN tb_daily_price p ON m.stock_code = p.stock_code 
                  AND c.published_at::date = p.date -- Simplified join for discovery
                WHERE p.date >= %s
            """, (start_date,))
            rows = cur.fetchall()
            
        if not rows:
            print("    No data found for scan.")
            return

        df = pl.DataFrame(rows)
        print(f"    Processing {len(df)} news-price pairs...")

        # 2. Tokenize and explode
        # (Memory Warning: This can be large. Process in chunks if needed)
        def get_tokens(text):
            return self.tokenizer.tokenize(text)

        df = df.with_columns(
            pl.col("content").map_elements(get_tokens, return_dtype=pl.List(pl.String)).alias("tokens")
        )
        
        df_tokens = df.select(["tokens", "excess_return"]).explode("tokens")
        df_tokens = df_tokens.with_columns(
            pl.col("excess_return").abs().alias("abs_return")
        )

        # 3. Aggregate stats per token
        stats = df_tokens.group_by("tokens").agg([
            pl.col("abs_return").mean().alias("avg_volatility"),
            pl.col("abs_return").count().alias("occurrence_count")
        ])

        # 4. Filter for Black Swans
        # Condition: Occurs enough to be real (>5 times) but rare globally (relative to total news)
        # and has high impact (> 3% avg absolute return)
        black_swans = stats.filter(
            (pl.col("occurrence_count") >= 5) & 
            (pl.col("avg_volatility") > 0.03) # 3% volatility threshold
        ).sort("avg_volatility", descending=True)

        print(f"    Discovered {len(black_swans)} black swan candidates.")

        # 5. Persist to DB
        with get_db_cursor() as cur:
            for row in black_swans.to_dicts():
                word = row['tokens']
                vol = float(row['avg_volatility'])
                count = int(row['occurrence_count'])
                
                # Impact score calculation (simple: vol * log1p(count))
                impact = float(vol * np.log1p(count))

                cur.execute("""
                    INSERT INTO tb_global_lexicon (word, avg_volatility, impact_score, occurrence_count, last_seen_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (word) DO UPDATE SET
                    avg_volatility = EXCLUDED.avg_volatility,
                    impact_score = EXCLUDED.impact_score,
                    occurrence_count = EXCLUDED.occurrence_count,
                    last_seen_at = CURRENT_TIMESTAMP
                """, (word, vol, impact, count))
        
        print("    Scan completed and results persisted.")

if __name__ == "__main__":
    scanner = GlobalDiscoveryScanner(horizon_days=180) # Test with 6 months
    scanner.scan()
