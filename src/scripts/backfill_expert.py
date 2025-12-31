# src/scripts/backfill_expert.py
import sys
import os
from datetime import datetime, date, timedelta
import json
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.db.connection import get_db_cursor
from src.predictor.scoring import Predictor
from src.nlp.tokenizer import Tokenizer
from src.utils.calendar import Calendar
from src.utils import calendar_helper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HistoricalExpertPredictor(Predictor):
    def fetch_news_by_date(self, stock_code, target_date, lag_limit=3):
        tokenizer = Tokenizer()
        news_by_lag = {}
        
        trading_days = Calendar.get_trading_days(stock_code)
        if not trading_days:
            return {}

        # The base date for the prediction
        target_impact_day = Calendar.get_impact_date(stock_code, target_date)
        
        idx = -1
        for i, d in enumerate(trading_days):
            if d == target_impact_day:
                idx = i
                break
        
        if idx == -1:
            return {}

        with get_db_cursor() as cur:
            for lag in range(1, lag_limit + 1):
                if idx - (lag - 1) < 0:
                    break
                    
                actual_impact_date = trading_days[idx - (lag - 1)]
                prev_trading_day = trading_days[idx - lag] if idx - lag >= 0 else actual_impact_date - timedelta(days=7)
                
                cur.execute("""
                    SELECT c.content, c.published_at
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    WHERE m.stock_code = %s 
                      AND c.published_at >= %s::timestamp + interval '7 hours'
                      AND c.published_at < %s::timestamp + interval '0 hours'
                """, (stock_code, prev_trading_day, actual_impact_date))
                
                rows = cur.fetchall()
                tokens = []
                market_open_dt = datetime.combine(actual_impact_date, datetime.min.time()) + timedelta(hours=9)
                
                for row in rows:
                    if row['content']:
                        pub_at = row['published_at']
                        if isinstance(pub_at, str):
                            pub_at = datetime.fromisoformat(pub_at)
                        
                        hours_diff = (market_open_dt - pub_at).total_seconds() / 3600.0
                        hours_diff = max(0, hours_diff)
                        import math
                        time_weight = math.exp(-0.02 * hours_diff)
                            
                        item_tokens = tokenizer.tokenize(row['content'])
                        for t in item_tokens:
                            tokens.append((t, time_weight))
                
                if tokens:
                    news_by_lag[lag] = tokens
                    
        return news_by_lag

def run_backfill(stock_code='005930'):
    predictor = HistoricalExpertPredictor()
    
    # 1. Get active model params
    with get_db_cursor() as cur:
        cur.execute("SELECT optimal_window_months, optimal_alpha FROM daily_targets WHERE stock_code = %s", (stock_code,))
        row = cur.fetchone()
        if not row:
            logger.error(f"No active model found for {stock_code}")
            return
        window = row['optimal_window_months']
        alpha = row['optimal_alpha']
        logger.info(f"Using active model: Window={window}, Alpha={alpha}")

    # 2. Set range to Nov 1st to Today
    start_date = date(2025, 11, 1)
    end_date = date.today()
    curr = start_date
    
    stats = {"success": 0, "skipped": 0, "holidays": 0}
    
    while curr <= end_date:
        if not calendar_helper.is_trading_day(curr.strftime('%Y-%m-%d')):
            logger.info(f"Skipping {curr} (Holiday)")
            stats["holidays"] += 1
            curr += timedelta(days=1)
            continue
            
        logger.info(f"Processing {curr}...")
        
        # A. Fetch news
        news = predictor.fetch_news_by_date(stock_code, curr)
        if not news:
            logger.warning(f"No news for {curr}, skipping.")
            stats["skipped"] += 1
            curr += timedelta(days=1)
            continue
            
        # B. Predict
        result = predictor.predict_advanced(stock_code, news)
        
        # C. Calculate return (Verification)
        actual_alpha = None
        is_correct = None
        
        trading_days = Calendar.get_trading_days(stock_code)
        idx = -1
        for i, d in enumerate(trading_days):
            if d == curr:
                idx = i
                break
        
        if idx != -1 and idx + 1 < len(trading_days):
            next_day = trading_days[idx + 1]
            with get_db_cursor() as cur:
                cur.execute("SELECT close_price FROM tb_daily_price WHERE stock_code = %s AND date = %s", (stock_code, curr))
                p1 = cur.fetchone()
                cur.execute("SELECT close_price FROM tb_daily_price WHERE stock_code = %s AND date = %s", (stock_code, next_day))
                p2 = cur.fetchone()
                
                if p1 and p2:
                    actual_alpha = (float(p2['close_price']) / float(p1['close_price'])) - 1.0
                    expected_alpha = result.get('expected_alpha', 0)
                    
                    if expected_alpha > 0 and actual_alpha > 0:
                        is_correct = True
                    elif expected_alpha < 0 and actual_alpha < 0:
                        is_correct = True
                    elif abs(expected_alpha) < 0.005 and abs(actual_alpha) < 0.005:
                        is_correct = True
                    else:
                        is_correct = False

        # D. Save to DB
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM tb_predictions WHERE stock_code = %s AND prediction_date = %s", (stock_code, curr))
            
            cur.execute("""
                INSERT INTO tb_predictions (
                    stock_code, prediction_date, sentiment_score, expected_alpha, 
                    actual_alpha, is_correct, status, top_keywords, evidence, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                stock_code, curr, 
                result.get('net_score', 0.0), result.get('expected_alpha', 0.0),
                actual_alpha, is_correct, result.get('status', 'Hold'),
                json.dumps(result.get('top_keywords', {})),
                json.dumps(result.get('evidence', [])),
            ))
            
        stats["success"] += 1
        curr += timedelta(days=1)

    logger.info(f"Expert backfill completed. Success: {stats['success']}, Skipped (No News): {stats['skipped']}, Holidays: {stats['holidays']}")

if __name__ == "__main__":
    run_backfill()
