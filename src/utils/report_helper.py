# src/utils/report_helper.py
import math
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.nlp.tokenizer import Tokenizer
from src.utils.calendar import Calendar

class ReportHelper:
    """
    Utility for generating evidence-based news narratives and reports.
    """
    
    @staticmethod
    def get_evidence_news(stock_code, target_date_str, score_map):
        """
        Calculates which news articles most influenced a prediction.
        Targeted for the "Why Gap" in consumer reports.
        """
        tokenizer = Tokenizer()
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        
        # 1. Get Trading Days context
        trading_days = Calendar.get_trading_days(stock_code, limit=100)
        try:
            idx = trading_days.index(target_date)
        except ValueError:
            return []

        # 2. Get Optimal Lag
        optimal_lag = 5
        with get_db_cursor() as cur:
            cur.execute("SELECT optimal_lag FROM daily_targets WHERE stock_code = %s", (stock_code,))
            row = cur.fetchone()
            if row and row['optimal_lag']:
                optimal_lag = int(row['optimal_lag'])

        news_evidence = []
        with get_db_cursor() as cur:
            for lag in range(1, optimal_lag + 1):
                if idx - (lag - 1) < 0: break
                
                actual_impact_date = trading_days[idx - (lag - 1)]
                if idx - lag >= 0:
                    prev_trading_day = trading_days[idx - lag]
                else:
                    prev_trading_day = actual_impact_date - timedelta(days=7)

                cur.execute("""
                    SELECT c.title, c.content, c.published_at, u.url, u.published_at_hint
                    FROM tb_news_content c
                    JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                    JOIN tb_news_url u ON c.url_hash = u.url_hash
                    WHERE m.stock_code = %s 
                      AND u.published_at_hint >= %s
                      AND u.published_at_hint < %s
                    ORDER BY c.published_at DESC
                """, (stock_code, prev_trading_day, actual_impact_date))
                
                rows = cur.fetchall()
                market_open_dt = datetime.combine(actual_impact_date, datetime.min.time()) + timedelta(hours=9)
                
                for r in rows:
                    content = (r['content'] or "") + " " + (r['title'] or "")
                    tokens = tokenizer.tokenize(content)
                    
                    base_score = 0.0
                    suffix = f"_L{lag}"
                    for t in tokens:
                        base_score += score_map.get(f"{t}{suffix}", 0.0)
                    
                    if base_score == 0: continue
                    
                    # Time Decay
                    pub_at = r['published_at']
                    hours_diff = max(0, (market_open_dt - pub_at).total_seconds() / 3600.0)
                    time_weight = math.exp(-0.02 * hours_diff)
                    
                    final_score = base_score * time_weight
                    
                    news_evidence.append({
                        "title": r['title'],
                        "url": r['url'],
                        "score": float(final_score),
                        "abs_score": abs(final_score),
                        "lag": lag
                    })

        news_evidence.sort(key=lambda x: x['abs_score'], reverse=True)
        return news_evidence[:10]

    @staticmethod
    def generate_narrative_summary(stock_code, target_date, evidence):
        """
        REQ-NARR: Automated 1-line narrative generation.
        """
        if not evidence:
            return "특이 뉴스 없음. 이전 심리 잔여물이 영향을 미치고 있습니다."
        
        top = evidence[0]
        sentiment = "긍정적" if top['score'] > 0 else "부정적"
        
        # Simple Template (Can be expanded to LLM call in Phase 9)
        narrative = f"[{sentiment}] '{top['title'][:40]}...' 등의 뉴스가 주된 심리 요인으로 작용하고 있습니다."
        return narrative
