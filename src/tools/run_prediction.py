# src/tools/run_prediction.py
"""
1년 학습 모델 기반 예측 및 검증 생성 스크립트
(이미 학습된 모델을 사용하여 예측만 수행)
Hybrid Logic (Main + Buffer) 포함
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.utils import calendar_helper
from src.nlp.tokenizer import Tokenizer
import json
import re

# 예측 기간 (Dec 22 ~ Jan 10, 3주)
PRED_START = datetime(2025, 12, 22)
PRED_END = datetime(2026, 1, 10)

STOCKS = [
    {"code": "005930", "name": "삼성전자", "version": "phase22_1y_samsung"},
    {"code": "000660", "name": "SK하이닉스", "version": "phase22_1y_skhynix"},
]

def generate_predictions(stock_code, version):
    """Generate predictions using the trained model in DB + Buffer"""
    print(f"  Generating predictions for {stock_code} ({version})...")
    
    # Initialize Tokenizer
    tokenizer = Tokenizer()
    
    with get_db_cursor() as cur:
        # Load Main sentiment dictionary
        cur.execute("""
            SELECT word, beta FROM tb_sentiment_dict
            WHERE stock_code = %s AND version = %s
        """, (stock_code, version))
        rows = cur.fetchall()
        
        # Pre-process dictionary
        sentiment_dict = {}
        for row in rows:
            raw_word = row['word']
            beta = float(row['beta'])
            base_word = re.sub(r'_L\d+$', '', raw_word)
            
            if base_word not in sentiment_dict:
                sentiment_dict[base_word] = 0.0
            sentiment_dict[base_word] += beta
            
        print(f"    [Main] 감성 단어: {len(sentiment_dict)}개 loaded.")
        
        # --- [Buffer Integration] ---
        # Load Buffer Dictionary (Source='Buffer', Version='daily_buffer')
        cur.execute("""
            SELECT word, beta FROM tb_sentiment_dict
            WHERE stock_code = %s AND source = 'Buffer' AND version = 'daily_buffer'
        """, (stock_code,))
        buffer_rows = cur.fetchall()
        
        buffer_count = 0
        for row in buffer_rows:
            raw_word = row['word']
            beta = float(row['beta'])
            base_word = re.sub(r'_L\d+$', '', raw_word)
            
            # Merge Logic: Add beta to existing or new
            if base_word not in sentiment_dict:
                sentiment_dict[base_word] = 0.0
                buffer_count += 1
            sentiment_dict[base_word] += beta
            
        print(f"    [Buffer] 감성 단어 추가/병합: {len(buffer_rows)}개 (New Unique: {buffer_count})")
        print(f"    [Hybrid] 최종 감성 단어: {len(sentiment_dict)}개")
        # ----------------------------
        
        # Load news from training window decay context
        news_fetch_start = PRED_START - timedelta(days=30)
        
        cur.execute("""
            SELECT c.content, c.published_at
            FROM tb_news_content c
            JOIN tb_news_mapping m ON c.url_hash = m.url_hash
            WHERE m.stock_code = %s AND c.published_at >= %s
            ORDER BY c.published_at DESC
        """, (stock_code, news_fetch_start))
        news_items = cur.fetchall()
        
        # Generate for each trading day
        current = PRED_START
        predictions_made = 0
        
        while current <= PRED_END:
            date_str = current.strftime('%Y-%m-%d')
            
            if calendar_helper.is_trading_day(date_str):
                total_score = 0.0
                news_count = 0
                daily_word_scores = {}

                for news in news_items:
                    content = news['content'] or ''
                    news_dt = news['published_at']
                    if not news_dt: continue
                    
                    if news_dt.date() > current.date():
                        continue
                        
                    days_ago = (current.date() - news_dt.date()).days
                    if days_ago > 30: 
                        continue
                    
                    decay = 0.95 ** days_ago if days_ago > 0 else 1.0
                    
                    # Use Tokenizer!
                    words = tokenizer.tokenize(content, n_gram=3) 
                    
                    article_hit = False
                    for w in words:
                        if w in sentiment_dict:
                            # Garbage Filter
                            clean = w.split('_L')[0]
                            if clean.isdigit(): continue
                            if len(clean) == 1 and clean.isalnum(): continue
                            
                            s = sentiment_dict[w]
                            contribution = s * decay
                            
                            if w not in daily_word_scores:
                                daily_word_scores[w] = 0.0
                            daily_word_scores[w] += contribution
                            
                            total_score += contribution
                            article_hit = True
                    
                    if article_hit:
                        news_count += 1
                
                # Extract Top 5 Pos / Top 5 Neg
                sorted_words = sorted(daily_word_scores.items(), key=lambda x: x[1], reverse=True)
                
                pos_words = [{"word": k, "score": v} for k, v in sorted_words if v > 0][:5]
                neg_words_sorted = sorted([item for item in daily_word_scores.items() if item[1] < 0], key=lambda x: x[1])
                neg_words = [{"word": k, "score": v} for k, v in neg_words_sorted][:5]
                
                if news_count > 0:
                    final_score = total_score / (news_count ** 0.5)
                else:
                    final_score = 0
                
                # Status determination
                if final_score > 2.0:
                    status, expected_alpha = "Super Buy", 0.15
                elif final_score > 0.5:
                    status, expected_alpha = "Cautious Buy", 0.05
                elif final_score < -2.0:
                    status, expected_alpha = "Super Sell", -0.15
                elif final_score < -0.5:
                    status, expected_alpha = "Cautious Sell", -0.05
                else:
                    status, expected_alpha = "Neutral", 0.0
                
                # Verification Logic (For Past Dates)
                actual_alpha = None
                is_correct = None
                
                # Try to fetch actual price return
                cur.execute("""
                    SELECT return_rate FROM tb_daily_price 
                    WHERE stock_code = %s AND date = %s
                """, (stock_code, date_str))
                price_row = cur.fetchone()
                
                if price_row:
                    actual_alpha = float(price_row['return_rate'])
                    # Directional Accuracy: (Score * Alpha > 0)
                    is_correct = (final_score * actual_alpha) > 0
                    
                    # Save Verification Result
                    cur.execute("""
                        INSERT INTO tb_verification_results 
                        (v_job_id, target_date, predicted_score, actual_alpha, is_correct, used_version)
                        VALUES (NULL, %s, %s, %s, %s, %s)
                    """, (date_str, final_score, actual_alpha, is_correct, version))
                    
                    print(f"    {date_str}: {status} (Score: {final_score:.2f}) | Actual: {actual_alpha*100:.2f}% [{'Hit' if is_correct else 'Miss'}]")
                else:
                    if current.date() <= datetime.now().date():
                        print(f"    {date_str}: {status} (Score: {final_score:.2f}) | Price Data Missing for Verification")
                    else:
                        print(f"    {date_str}: {status} (Score: {final_score:.2f})")

                # Delete & Insert Prediction
                cur.execute("DELETE FROM tb_predictions WHERE stock_code = %s AND prediction_date = %s", 
                           (stock_code, date_str))
                cur.execute("""
                    INSERT INTO tb_predictions (
                        stock_code, prediction_date, sentiment_score, expected_alpha, status, intensity, top_keywords,
                        actual_alpha, is_correct
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    stock_code, date_str, final_score, expected_alpha, status,
                    min(abs(final_score) / 5.0, 1.0),
                    json.dumps({
                        "version": version + "_hybrid", 
                        "news_count": news_count,
                        "positive": pos_words,
                        "negative": neg_words
                    }),
                    actual_alpha, is_correct
                ))
                
                predictions_made += 1
            
            current += timedelta(days=1)
        
        print(f"    총 {predictions_made}개 예측 생성")

def create_verification_job(stock_code, version):
    """Create a verification job entry"""
    # Simply log it as MANUAL_PREDICT
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, params, status, started_at, completed_at)
            VALUES (%s, 'MANUAL_PREDICT_HYBRID', %s, 'completed', %s, CURRENT_TIMESTAMP)
            RETURNING v_job_id
        """, (
            stock_code,
            json.dumps({"version": version, "mode": "Hybrid"}),
            datetime.now() - timedelta(minutes=1)
        ))
        v_job_id = cur.fetchone()['v_job_id']
    return v_job_id

def main():
    print("\n" + "="*70)
    print("  N-SentiTrader 예측 및 검증 (Hybrid Logic)")
    print("  학습 스킵 -> 기존 모델 사용")
    print("="*70)
    
    results = []
    for stock in STOCKS:
        print(f"\n[{stock['name']}]")
        generate_predictions(stock["code"], stock["version"])
        v_job_id = create_verification_job(stock["code"], stock["version"])
        results.append({"stock": stock, "v_job_id": v_job_id})
        
    print("\n" + "="*70)
    print("  🎉 예측 갱신 완료!")
    for r in results:
        print(f"  {r['stock']['name']}: Job #{r['v_job_id']}")

if __name__ == "__main__":
    main()
