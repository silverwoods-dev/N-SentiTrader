import time
import schedule
import logging
from datetime import datetime
from src.collector.news import JobManager
from src.learner.lasso import LassoLearner
from src.predictor.scoring import Predictor
from src.db.connection import get_db_connection

from src.utils.metrics import start_metrics_server

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_daily_pipeline():
    logger.info("Starting daily pipeline...")
    
    try:
        # 1. Job Manager: Daily 수집 시작
        manager = JobManager()
        manager.start_daily_jobs()
        logger.info("Daily collection jobs started.")
        
        # 여기서 수집 완료를 보장하기 위해 약간의 대기 또는 상태 체크 필요
        # 데일리 수집은 보통 몇 분 내에 종료됨
        time.sleep(60) 
        
        # 2. 모든 활성 타겟에 대해 분석 파이프라인 가동
        from src.learner.manager import AnalysisManager
        from src.db.connection import get_db_cursor
        
        with get_db_cursor() as cur:
            cur.execute("SELECT stock_code FROM daily_targets WHERE status = 'active'")
            active_targets = cur.fetchall()
            
        for target in active_targets:
            stock_code = target['stock_code']
            am = AnalysisManager(stock_code)
            
            # 주간 학습 (Main Dict) - 매주 월요일 또는 메인 사전이 없을 때 실행하도록 고도화 가능
            # 여기서는 매일 버퍼 업데이트만 수행하고, 메인 사전은 필요 시 수동/정기 실행
            am.run_daily_update()
            logger.info(f"Daily buffer update completed for {stock_code}")
        
        # 3. 예측 (Predictor)
        predictor = Predictor()
        # v1_main 버전을 기본으로 사용 (버전 관리 로직 고도화 필요)
        predictor.run_daily_prediction(version="v1_main")
        logger.info("Daily prediction completed.")
        
    except Exception as e:
        logger.error(f"Error in daily pipeline: {e}")

def check_immediate_tasks():
    """
    즉시 실행이 필요한 작업(예: 신규 종목 활성화 요청)이 있는지 확인
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 활성화 요청된 종목 확인 (activation_requested_at이 있고 status가 paused인 경우)
                cur.execute("""
                    SELECT stock_code FROM daily_targets 
                    WHERE status = 'paused' AND activation_requested_at IS NOT NULL
                """)
                rows = cur.fetchall()
                for row in rows:
                    stock_code = row[0]
                    logger.info(f"Activating daily collection for {stock_code}")
                    cur.execute("""
                        UPDATE daily_targets 
                        SET status = 'active', activation_requested_at = NULL 
                        WHERE stock_code = %s
                    """, (stock_code,))
                conn.commit()
    except Exception as e:
        logger.error(f"Error checking immediate tasks: {e}")

def main():
    logger.info("N-SentiTrader Scheduler started.")
    start_metrics_server()
    
    # 매일 오전 8시에 파이프라인 실행
    schedule.every().day.at("08:00").do(run_daily_pipeline)
    
    # 1분마다 즉시 실행 작업 확인
    schedule.every(1).minutes.do(check_immediate_tasks)
    
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()
