import logging
import json
from datetime import datetime, timedelta
from src.learner.manager import AnalysisManager
from src.predictor.scoring import Predictor
from src.db.connection import get_db_cursor
from src.utils.calendar import Calendar

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("RefineSamsung")

def manual_refine_005930():
    stock_code = "005930" # Samsung Electronics
    
    # 1. Training Setup (1 month ending Dec 19, 2025 - To avoid data leakage for Dec 22+)
    am = AnalysisManager(stock_code)
    train_end = "2025-12-19" # Friday before the current week
    train_start = (datetime.strptime(train_end, '%Y-%m-%d') - timedelta(days=30)).strftime('%Y-%m-%d')
    
    logger.info(f"--- [Phase 8] Starting Manual Refinement for {stock_code} ---")
    logger.info(f"Training Range: {train_start} ~ {train_end}")
    
    # Run training
    # Version name: 'phase8_refined'
    am.learner.run_training(stock_code, train_start, train_end, version='phase8_refined', source='Main', is_active=True)
    
    logger.info("Training completed. dictionary saved with version 'phase8_refined' and marked as ACTIVE.")
    
    # 2. Prediction Cleanup
    # Remove existing predictions for this week and next week to avoid duplicates
    with get_db_cursor() as cur:
        cur.execute("DELETE FROM tb_predictions WHERE stock_code = %s AND prediction_date >= '2025-12-22'", (stock_code,))
        logger.info(f"Cleared old predictions for {stock_code} from 2025-12-22 onwards.")

    # 3. Prediction Generation (Dec 22 ~ Jan 2)
    predictor = Predictor()
    
    # We want to generate predictions for each trading day in the range
    # Note: 12/25 is holiday, but we want to populate tb_predictions so the UI sees something,
    # OR we let the UI's calendar logic handle it.
    # Actually, the UI pulls from tb_predictions. If row is missing, it shows 'PENDING'.
    # If we want to show 'Buy/Sell' for 22, 23, 24, 26, we must generate them.
    
    target_dates = [
        "2025-12-22", "2025-12-23", "2025-12-24", "2025-12-26", # This Week (25 skipped)
        "2025-12-29", "2025-12-30", "2026-01-02"  # Next Week (31, 1 skipped)
    ]
    
    # For simplicity, we'll try to fetch news for each of these days.
    # Since fetch_news_by_lag in Predictor is hardcoded to use 'today's impact date',
    # we'll create a slightly modified version or call it with careful mocking if possible.
    # Actually, let's just use the core logic directly for these 10 days.
    
    for target_day_str in target_dates:
        target_day = datetime.strptime(target_day_str, '%Y-%m-%d').date()
        logger.info(f"Generating prediction for {target_day_str}...")
        
        # We need news for this target day.
        # In our system, news for T comes from [PrevTradingDay 16:00, T 16:00].
        # We'll use predictor.fetch_news_by_lag logic but for a specific date.
        news_by_lag = fetch_news_for_date(stock_code, target_day)
        
        if not news_by_lag:
            logger.warning(f"No news found for {target_day_str}. Skipping.")
            continue
            
        res = predictor.predict_advanced(stock_code, news_by_lag, version='phase8_refined')
        
        with get_db_cursor() as cur:
            cur.execute("""
                INSERT INTO tb_predictions 
                (stock_code, prediction_date, sentiment_score, intensity, status, expected_alpha, confidence_score, top_keywords) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                stock_code, 
                target_day,
                res['net_score'], 
                res['intensity'], 
                res['status'], 
                res['expected_alpha'], 
                res['confidence_score'],
                json.dumps(res['top_keywords'])
            ))
            logger.info(f"  Result: {res['status']} (Alpha: {res['expected_alpha']:.4f})")

    logger.info("--- [Phase 8] Manual Refinement & Prediction Task Completed ---")

def fetch_news_for_date(stock_code, target_date, lag_limit=5):
    """
    Predictor.fetch_news_by_lag의 로직을 특정 날짜 기준으로 재현합니다.
    """
    from src.nlp.tokenizer import Tokenizer
    import math
    tokenizer = Tokenizer()
    news_by_lag = {}
    
    trading_days = Calendar.get_trading_days(stock_code)
    
    # target_date가 trading_days에 있는지 확인, 없으면 캘린더 fallback 사용
    if target_date not in trading_days:
        # 12/26 같은 미래 날짜는 DB에 없을 수 있음.
        # 하지만 뉴스는 이미 쌓여있을 수 있으므로, 캘린더를 통해 'Impact Date'로서의 유효성만 확인
        pass

    # idx를 target_date 위치로 잡음
    idx = -1
    for i, d in enumerate(trading_days):
        if d == target_date:
            idx = i
            break
    
    # 만약 DB(tb_daily_price)에 없는 미래 날짜라면, 가장 마지막 인덱스 + (차이) 로 시뮬레이션
    if idx == -1:
        # 단순화: 가장 최근 거래일로부터 며칠 떨어졌는지 계산
        last_day = trading_days[-1]
        # trade_days_diff = (target_date - last_day).days # 이건 비영업일 포함이라 위험함
        # 여기서는 그냥 idx를 len - 1로 두고, target_date를 직접 쿼리에 사용
        idx = len(trading_days) - 1

    with get_db_cursor() as cur:
        for lag in range(1, lag_limit + 1):
            # lag 1의 기준 일자 (target_date)
            # lag 2의 기준 일자 (target_date의 1일전 영업일)
            
            # 실제 '이전 영업일' 계산이 필요함
            # 여기서는 편의상 target_date와 그 전날들을 탐색
            # 실제로는 Calendar 클래스의 도움을 받는 것이 좋음
            
            # target_date 기준 lag-1 번째 이전 영업일 찾기
            # (매우 거칠게 구현: 주말 제외 1일씩 뒤로 감)
            curr_impact_date = target_date
            # lag-1 번 만큼 이전 영업일로 이동
            l = lag - 1
            while l > 0:
                curr_impact_date -= timedelta(days=1)
                if curr_impact_date.weekday() < 5: # Sat=5, Sun=6
                    l -= 1
            
            # prev_trading_day 찾기 (curr_impact_date의 바로 전 영업일)
            prev_day = curr_impact_date - timedelta(days=1)
            while prev_day.weekday() >= 5:
                prev_day -= timedelta(days=1)
                
            cur.execute("""
                SELECT c.content, c.published_at
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s 
                  AND c.published_at >= %s::timestamp + interval '16 hours'
                  AND c.published_at < %s::timestamp + interval '16 hours'
            """, (stock_code, prev_day, curr_impact_date))
            
            rows = cur.fetchall()
            tokens = []
            market_open_dt = datetime.combine(curr_impact_date, datetime.min.time()) + timedelta(hours=9)
            
            for row in rows:
                if row['content']:
                    pub_at = row['published_at']
                    hours_diff = (market_open_dt - pub_at).total_seconds() / 3600.0
                    hours_diff = max(0, hours_diff)
                    time_weight = math.exp(-0.02 * hours_diff)
                    
                    item_tokens = tokenizer.tokenize(row['content'])
                    for t in item_tokens:
                        tokens.append((t, time_weight))
            
            if tokens:
                news_by_lag[lag] = tokens
                
    return news_by_lag

if __name__ == "__main__":
    manual_refine_005930()
