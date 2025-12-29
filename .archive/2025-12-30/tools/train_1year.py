# src/tools/train_1year.py
"""
1년 학습 및 2주 예측 통합 스크립트 (Phase 22)
삼성전자(005930)와 SK하이닉스(000660)를 모두 처리
Vocabulary Collapse 문제를 해결하기 위해 학습 기간을 1년으로 확장
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.learner.lasso import LassoLearner
from src.utils import calendar_helper
import json

# 1년 학습 (Dec 19, 2024 ~ Dec 19, 2025)
# 정확히 365일 전부터
TRAIN_END = datetime(2025, 12, 19)
TRAIN_START = TRAIN_END - timedelta(days=365)

# 예측 기간 (Dec 22 ~ Jan 10, 3주)
PRED_START = datetime(2025, 12, 22)
PRED_END = datetime(2026, 1, 10)

STOCKS = [
    {"code": "005930", "name": "삼성전자", "version": "phase22_1y_samsung"},
    {"code": "000660", "name": "SK하이닉스", "version": "phase22_1y_skhynix"},
]

def train_stock(stock_code, stock_name, version):
    """Train a stock with 1 year of data"""
    print(f"\n{'='*60}")
    print(f"  {stock_name} ({stock_code}) - 1년 학습 (Phase 22)")
    print(f"  학습 기간: {TRAIN_START.date()} ~ {TRAIN_END.date()}")
    print(f"{'='*60}")
    
    # 1. Check news availability
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM tb_news_content c
            JOIN tb_news_mapping m ON c.url_hash = m.url_hash
            WHERE m.stock_code = %s AND c.published_at BETWEEN %s AND %s
        """, (stock_code, TRAIN_START, TRAIN_END))
        news_count = cur.fetchone()['cnt']
        print(f"[✓] 뉴스 데이터: {news_count}건")
    
    # 2. Train model
    print(f"[1/3] 모델 학습 중...")
    # alpha reduced to 1e-6 to force larger vocabulary (Fix for Phase 22 sparsity)
    learner = LassoLearner(alpha=0.000001) 
    learner.run_training(
        stock_code=stock_code,
        start_date=TRAIN_START.strftime('%Y-%m-%d'),
        end_date=TRAIN_END.strftime('%Y-%m-%d'),
        version=version,
        source='Main',
        is_active=True
    )
    print(f"[✓] 학습 완료: {version}")
    
    # 3. Generate predictions
    print(f"[2/3] 예측 생성 중 (일별 키워드 추출 포함)...")
    generate_predictions(stock_code, version)
    
    # 4. Create verification job
    print(f"[3/3] 검증 보고서 생성 중...")
    v_job_id = create_verification_job(stock_code, version)
    
    print(f"\n[✅] {stock_name} 완료!")
    print(f"    소비자 대시보드: http://localhost:8081/analytics/outlook?stock_code={stock_code}")
    print(f"    전문가 대시보드: http://localhost:8081/analytics/expert?stock_code={stock_code}&v_job_id={v_job_id}")
    
    return v_job_id

from src.nlp.tokenizer import Tokenizer
import re

def generate_predictions(stock_code, version):
    """Generate predictions using the trained model"""
    
    # Initialize Tokenizer
    tokenizer = Tokenizer()
    
    with get_db_cursor() as cur:
        # Load sentiment dictionary
        cur.execute("""
            SELECT word, beta FROM tb_sentiment_dict
            WHERE stock_code = %s AND version = %s
        """, (stock_code, version))
        rows = cur.fetchall()
        
        # Pre-process dictionary: Strip _L suffix and aggregate scores
        # Logic: If 'AI_L1' is 0.5 and 'AI_L2' is 0.3, base sentiment is 0.8?
        # Or should we take the strongest? Summing is safer for 'net impact'.
        sentiment_dict = {}
        for row in rows:
            raw_word = row['word']
            beta = float(row['beta'])
            
            # Remove _L1, _L2, etc.
            base_word = re.sub(r'_L\d+$', '', raw_word)
            
            if base_word not in sentiment_dict:
                sentiment_dict[base_word] = 0.0
            sentiment_dict[base_word] += beta
        
        # --- [Buffer Integration] ---
        # Load Buffer Dictionary (Source='Buffer', Version='daily_buffer')
        print(f"    [Main] 감성 단어: {len(sentiment_dict)}개 loaded.")
        
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

        # Load news from training window (Last 30 days sufficient for decay context)
        # Dec 22 predictions need news from Dec 21, 20...
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
                    
                    # Skip future news relative to prediction date
                    if news_dt.date() > current.date():
                        continue
                        
                    days_ago = (current.date() - news_dt.date()).days
                    # Skip old news > 30 days
                    if days_ago > 30: 
                        continue
                    
                    decay = 0.95 ** days_ago if days_ago > 0 else 1.0
                    
                    # Use Tokenizer!
                    words = tokenizer.tokenize(content, n_gram=3) # Match training n-gram
                    
                    article_hit = False
                    for w in words:
                        if w in sentiment_dict:
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
                
                # Delete & Insert
                cur.execute("DELETE FROM tb_predictions WHERE stock_code = %s AND prediction_date = %s", 
                           (stock_code, date_str))
                cur.execute("""
                    INSERT INTO tb_predictions (stock_code, prediction_date, sentiment_score, expected_alpha, status, intensity, top_keywords)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    stock_code, date_str, final_score, expected_alpha, status,
                    min(abs(final_score) / 5.0, 1.0),
                    json.dumps({
                        "version": version, 
                        "news_count": news_count,
                        "positive": pos_words,
                        "negative": neg_words
                    })
                ))
                
                predictions_made += 1
                if predictions_made % 5 == 0:
                    print(f"    {date_str}: {status} (score: {final_score:.2f})")
            
            current += timedelta(days=1)
        
        print(f"    총 {predictions_made}개 예측 생성")

def create_verification_job(stock_code, version):
    """Create a verification job entry"""
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, params, status, started_at, completed_at)
            VALUES (%s, 'MANUAL_1Y_TRAIN', %s, 'completed', %s, CURRENT_TIMESTAMP)
            RETURNING v_job_id
        """, (
            stock_code,
            json.dumps({
                "train_start": TRAIN_START.strftime('%Y-%m-%d'),
                "train_end": TRAIN_END.strftime('%Y-%m-%d'),
                "pred_start": PRED_START.strftime('%Y-%m-%d'),
                "pred_end": PRED_END.strftime('%Y-%m-%d'),
                "version": version,
                "train_days": 365
            }),
            datetime.now() - timedelta(minutes=15)
        ))
        v_job_id = cur.fetchone()['v_job_id']
        
        # Add verification results from predictions
        cur.execute("""
            SELECT prediction_date, sentiment_score, expected_alpha, status
            FROM tb_predictions
            WHERE stock_code = %s AND prediction_date BETWEEN %s AND %s
            ORDER BY prediction_date
        """, (stock_code, PRED_START, PRED_END))
        
        predictions = cur.fetchall()
        for pred in predictions:
            cur.execute("""
                INSERT INTO tb_verification_results (v_job_id, target_date, predicted_score, actual_alpha, is_correct, used_version)
                VALUES (%s, %s, %s, NULL, NULL, %s)
            """, (v_job_id, pred['prediction_date'], float(pred['sentiment_score'] or 0), version))
        
        print(f"    검증 Job #{v_job_id} 생성 ({len(predictions)}개 엔트리)")
        return v_job_id

def main():
    print("\n" + "="*70)
    print("  N-SentiTrader 1년 학습 (Phase 22)")
    print("  대상: 삼성전자(005930), SK하이닉스(000660)")
    print(f"  학습 기간: {TRAIN_START.date()} ~ {TRAIN_END.date()} (365일)")
    print(f"  예측 기간: {PRED_START.date()} ~ {PRED_END.date()}")
    print("="*70)
    
    results = []
    for stock in STOCKS:
        v_job_id = train_stock(stock["code"], stock["name"], stock["version"])
        results.append({"stock": stock, "v_job_id": v_job_id})
    
    print("\n" + "="*70)
    print("  🎉 전체 작업 완료!")
    print("="*70)
    for r in results:
        print(f"\n  {r['stock']['name']} ({r['stock']['code']}):")
        print(f"    - 모델 버전: {r['stock']['version']}")
        print(f"    - 검증 Job: #{r['v_job_id']}")
        print(f"    - 소비자: http://localhost:8081/analytics/outlook?stock_code={r['stock']['code']}")

if __name__ == "__main__":
    main()
