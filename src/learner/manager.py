# src/learner/manager.py
import polars as pl
from datetime import datetime, timedelta
from src.learner.lasso import LassoLearner
from src.db.connection import get_db_cursor
import logging

logger = logging.getLogger(__name__)

class AnalysisManager:
    def __init__(self, stock_code):
        self.stock_code = stock_code
        self.learner = LassoLearner()

    def check_data_availability(self, days_needed=90):
        """
        최소 3개월(90일) 이상의 뉴스 및 가격 데이터가 있는지 확인합니다.
        """
        with get_db_cursor() as cur:
            # 주가 데이터 확인
            cur.execute("""
                SELECT COUNT(*) as count, MIN(date) as min_date, MAX(date) as max_date 
                FROM tb_daily_price WHERE stock_code = %s
            """, (self.stock_code,))
            price_row = cur.fetchone()
            
            # 뉴스 데이터 확인
            cur.execute("""
                SELECT COUNT(DISTINCT c.published_at::date) as date_count
                FROM tb_news_content c
                JOIN tb_news_mapping m ON c.url_hash = m.url_hash
                WHERE m.stock_code = %s
            """, (self.stock_code,))
            news_row = cur.fetchone()
            
        if not price_row or not news_row:
            return False, 0
            
        days_span = (price_row['max_date'] - price_row['min_date']).days
        news_days = news_row['date_count']
        
        logger.info(f"Data Check for {self.stock_code}: Price Days={days_span}, News Days={news_days}")
        
        # 주가와 정보가 모두 일정 기간 이상 있어야 함
        return (days_span >= days_needed - 10 and news_days >= days_needed * 0.5), days_span

    def run_daily_update(self):
        """
        매일 실행되는 버퍼 사전 업데이트 (최근 7일)
        """
        logger.info(f"Running daily buffer update for {self.stock_code}")
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        # Buffer 사전 학습
        self.learner.run_training(
            self.stock_code, 
            start_date.strftime('%Y-%m-%d'), 
            end_date.strftime('%Y-%m-%d'), 
            version="daily_buffer", 
            source="Buffer"
        )
        return True

    def run_full_pipeline(self):
        """
        1. 데이터 확인
        2. 최적 시차 도출
        3. Main Dictionary 학습 (2개월)
        4. Buffer Dictionary 초기 학습 (1주일)
        """
        available, days = self.check_data_availability(90)
        if not available:
            logger.warning(f"Not enough data for {self.stock_code} ({days} days found).")
            return False

        # 날짜 계산
        end_date = datetime.now().date()
        train_end = end_date - timedelta(days=1)
        train_start = train_end - timedelta(days=60)
        
        t_start_str = train_start.strftime('%Y-%m-%d')
        t_end_str = train_end.strftime('%Y-%m-%d')

        logger.info(f"Starting full pipeline for {self.stock_code}: Train({t_start_str}~{t_end_str})")

        # 1. 최적 시차 도출
        optimal_lag = self.learner.find_optimal_lag(self.stock_code, t_start_str, t_end_str)
        self.learner.lags = optimal_lag

        # 2. Main Dictionary 학습
        self.learner.run_training(self.stock_code, t_start_str, t_end_str, version="v1_main", source="Main")

        # 3. Buffer Dictionary 초기 학습
        self.run_daily_update()

        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    am = AnalysisManager("005930")
    am.run_full_pipeline()
