# src/learner/discovery_engine.py
import polars as pl
import numpy as np
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.nlp.tokenizer import Tokenizer
import logging

logger = logging.getLogger(__name__)

class ContentDiscoveryEngine:
    def __init__(self, lookback_years=3, sigma_threshold=3.0):
        self.lookback_years = lookback_years
        self.sigma_threshold = sigma_threshold
        self.tokenizer = Tokenizer()
        
    def fetch_market_tail_events(self):
        """
        Fetches all stock-days where absolute return > 3 * Sigma (Global or Stock-Specific)
        For simplicity and robustness, we use Stock-Specific Sigma.
        """
        print(f"Scanning market for {self.sigma_threshold}-sigma events over last {self.lookback_years} years...")
        
        start_date = (datetime.now() - timedelta(days=365 * self.lookback_years)).strftime('%Y-%m-%d')
        
        with get_db_cursor() as cur:
            # 1. Calculate Per-Stock Volatility (Sigma) and Daily Returns
            # extracting high outliers
            
            # This query finds events where abs(return) > 3 * stddev(return)
            # We do this in SQL for efficiency? Or fetch all and process in Polars?
            # Creating a CTE for stats is better.
            
            sql = """
                WITH stock_stats AS (
                    SELECT 
                        stock_code,
                        STDDEV(return_rate) as sigma,
                        AVG(return_rate) as mu
                    FROM tb_daily_price
                    WHERE date >= %s
                    GROUP BY stock_code
                    HAVING COUNT(*) > 200 -- Ensure valid history
                )
                SELECT 
                    p.date,
                    p.stock_code,
                    p.return_rate,
                    s.sigma
                FROM tb_daily_price p
                JOIN stock_stats s ON p.stock_code = s.stock_code
                WHERE p.date >= %s
                  AND ABS(p.return_rate - s.mu) > (s.sigma * %s)
            """
            cur.execute(sql, (start_date, start_date, self.sigma_threshold))
            events = cur.fetchall()
            
        print(f"Found {len(events)} tail events.")
        return pl.DataFrame(events)

    def analyze_tail_keywords(self, tail_events_df: pl.DataFrame):
        """
        For each tail event, fetch associated news and extract keywords.
        """
        if tail_events_df.is_empty():
            return {}
            
        # Group by stock to batch fetch news? 
        # Or just iterate. 3000 events might be slow one by one.
        # Let's aggregate by date-stock.
        
        # We need to map Price Date -> Impact Date (News Date)
        # News impacting T usually comes from T-1 16:00 to T 15:30.
        # Simplified: Fetch news published on T-1 and T (up to close).
        
        print("Fetching news for tail events...")
        
        tail_word_counts = {}
        
        # Unique list of (stock_code, date)
        targets = tail_events_df.select(["stock_code", "date"]).unique().to_dicts()
        
        with get_db_cursor() as cur:
            for i, target in enumerate(targets):
                if i % 100 == 0:
                    print(f"  Processed {i}/{len(targets)} events...")
                    
                stock_code = target['stock_code']
                target_date = target['date'] # Date object
                
                # Fetch news for this event (Window: T-1 to T)
                # target_date is a date object.
                prev_date = target_date - timedelta(days=1)
                
                cur.execute("""
                    SELECT c.content 
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s
                      AND c.published_at::date BETWEEN %s AND %s
                """, (stock_code, prev_date, target_date))
                
                rows = cur.fetchall()
                for row in rows:
                    if row['content']:
                        tokens = self.tokenizer.tokenize(row['content']) # Returns list of strings
                        for token in tokens:
                            tail_word_counts[token] = tail_word_counts.get(token, 0) + 1
                            
        return tail_word_counts

    def run_discovery(self, min_occurrence=5):
        events_df = self.fetch_market_tail_events()
        if events_df.is_empty():
            print("No events found.")
            return []
            
        word_counts = self.analyze_tail_keywords(events_df)
        
        # Sort by frequency in tail events
        # In a real impl, we would compare this P(w|Tail) vs P(w|Global) to find "Lift".
        # For now, raw frequency in Black Swan events is a good proxy for "Crisis Words".
        
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        print(f"\nTop Discovered Black Swan Keywords (Min Occur: {min_occurrence}):")
        results = []
        for word, count in sorted_words:
            if count >= min_occurrence:
                print(f"  {word}: {count}")
                results.append(word)
                
        return results

if __name__ == "__main__":
    engine = ContentDiscoveryEngine()
    engine.run_discovery()
