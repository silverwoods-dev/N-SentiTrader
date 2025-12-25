# src/tools/train_3month.py
"""
3개월 학습 및 2주 예측 통합 스크립트
삼성전자(005930)와 SK하이닉스(000660)를 모두 처리
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.learner.lasso import LassoLearner
from src.utils import calendar_helper
import json

# 3개월 학습 (Sep 19 ~ Dec 19)
TRAIN_END = datetime(2025, 12, 19)
TRAIN_START = TRAIN_END - timedelta(days=90)

# 예측 기간 (Dec 22 ~ Jan 10, 3주)
PRED_START = datetime(2025, 12, 22)
PRED_END = datetime(2026, 1, 10)

STOCKS = [
    {"code": "005930", "name": "삼성전자", "version": "phase14_3m_samsung"},
    {"code": "000660", "name": "SK하이닉스", "version": "phase14_3m_skhynix"},
]

def train_stock(stock_code, stock_name, version):
    """Train a stock with 3 months of data"""
    print(f"\n{'='*60}")
    print(f"  {stock_name} ({stock_code}) - 3개월 학습")
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
    learner = LassoLearner()
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
    print(f"[2/3] 예측 생성 중...")
    generate_predictions(stock_code, version)
    
    # 4. Create verification job
    print(f"[3/3] 검증 보고서 생성 중...")
    v_job_id = create_verification_job(stock_code, version)
    
    print(f"\n[✅] {stock_name} 완료!")
    print(f"    소비자 대시보드: http://localhost:8081/analytics/outlook?stock_code={stock_code}")
    print(f"    전문가 대시보드: http://localhost:8081/analytics/expert?stock_code={stock_code}&v_job_id={v_job_id}")
    
    return v_job_id

def generate_predictions(stock_code, version):
    """Generate predictions using the trained model"""
    with get_db_cursor() as cur:
        # Load sentiment dictionary
        cur.execute("""
            SELECT word, beta FROM tb_sentiment_dict
            WHERE stock_code = %s AND version = %s
        """, (stock_code, version))
        sentiment_dict = {row['word']: float(row['beta']) for row in cur.fetchall()}
        
        if not sentiment_dict:
            cur.execute("""
                SELECT word, beta FROM tb_sentiment_dict
                WHERE stock_code = %s ORDER BY updated_at DESC LIMIT 500
            """, (stock_code,))
            sentiment_dict = {row['word']: float(row['beta']) for row in cur.fetchall()}
        
        print(f"    감성 단어 로드: {len(sentiment_dict)}개")
        
        # Load news from training window
        cur.execute("""
            SELECT c.content, c.published_at
            FROM tb_news_content c
            JOIN tb_news_mapping m ON c.url_hash = m.url_hash
            WHERE m.stock_code = %s AND c.published_at BETWEEN %s AND %s
            ORDER BY c.published_at DESC
        """, (stock_code, TRAIN_START, TRAIN_END))
        news_items = cur.fetchall()
        
        # Generate for each trading day
        current = PRED_START
        predictions_made = 0
        
        while current <= PRED_END:
            date_str = current.strftime('%Y-%m-%d')
            
            if calendar_helper.is_trading_day(date_str):
                total_score = 0.0
                news_count = 0
                
                for news in news_items:
                    content = news['content'] or ''
                    pub_date = news['published_at'].date() if news['published_at'] else TRAIN_END.date()
                    days_ago = (current.date() - pub_date).days
                    
                    decay = 0.95 ** days_ago if days_ago > 0 else 1.0
                    words = content.lower().split()
                    article_score = sum(sentiment_dict.get(w, 0) for w in words)
                    
                    if article_score != 0:
                        total_score += article_score * decay
                        news_count += 1
                
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
                    json.dumps({"version": version, "news_count": news_count})
                ))
                
                predictions_made += 1
                print(f"    {date_str}: {status} (score: {final_score:.2f})")
            
            current += timedelta(days=1)
        
        print(f"    총 {predictions_made}개 예측 생성")

def create_verification_job(stock_code, version):
    """Create a verification job entry"""
    with get_db_cursor() as cur:
        cur.execute("""
            INSERT INTO tb_verification_jobs (stock_code, v_type, params, status, started_at, completed_at)
            VALUES (%s, 'MANUAL_3M_TRAIN', %s, 'completed', %s, CURRENT_TIMESTAMP)
            RETURNING v_job_id
        """, (
            stock_code,
            json.dumps({
                "train_start": TRAIN_START.strftime('%Y-%m-%d'),
                "train_end": TRAIN_END.strftime('%Y-%m-%d'),
                "pred_start": PRED_START.strftime('%Y-%m-%d'),
                "pred_end": PRED_END.strftime('%Y-%m-%d'),
                "version": version,
                "train_days": 90
            }),
            datetime.now() - timedelta(minutes=5)
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
    print("  N-SentiTrader 3개월 학습 및 보고서 생성")
    print("  대상: 삼성전자(005930), SK하이닉스(000660)")
    print(f"  학습 기간: {TRAIN_START.date()} ~ {TRAIN_END.date()} (90일)")
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
        print(f"    - 전문가: http://localhost:8081/analytics/expert?stock_code={r['stock']['code']}&v_job_id={r['v_job_id']}")

if __name__ == "__main__":
    main()
