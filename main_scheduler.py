import time
import schedule
import logging
from datetime import datetime
from src.collector.news import JobManager
from src.learner.lasso import LassoLearner
from src.predictor.scoring import Predictor
from src.db.connection import get_db_connection

from src.utils.metrics import start_metrics_server
import json
from src.utils.mq import publish_job

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

def recover_stale_jobs():
    """
    running 상태인데 updated_at이 10분 이상 지난 스테일 잡을 탐지하여 회복 시도
    """
    logger.info("Checking for stale jobs...")
    try:
        from src.db.connection import get_db_cursor
        
        # 1. 일반 Jobs (backfill 등)
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT job_id, params, retry_count 
                FROM jobs 
                WHERE status = 'running' 
                AND updated_at < NOW() - INTERVAL '10 minutes'
            """)
            stale_jobs = cur.fetchall()
            
            for job in stale_jobs:
                job_id = job['job_id']
                params = job['params']
                if isinstance(params, str):
                    params = json.loads(params)
                
                retry_count = job['retry_count']
                
                if retry_count < 3: # Max 3 retries
                    logger.warning(f"Stale Job #{job_id} detected. Resetting to pending (Retry: {retry_count + 1})")
                    cur.execute("""
                        UPDATE jobs 
                        SET status = 'pending', retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP 
                        WHERE job_id = %s
                    """, (job_id,))
                    
                    # MQ에 다시 투입
                    params['job_id'] = job_id
                    publish_job(params)
                else:
                    logger.error(f"Stale Job #{job_id} exceeded max retries. Marking as failed.")
                    cur.execute("""
                        UPDATE jobs 
                        SET status = 'failed', updated_at = CURRENT_TIMESTAMP 
                        WHERE job_id = %s
                    """, (job_id,))

        # 2. Backtest Verification Jobs
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT v_job_id, retry_count 
                FROM tb_verification_jobs 
                WHERE status = 'running' 
                AND updated_at < NOW() - INTERVAL '15 minutes'
            """)
            stale_v_jobs = cur.fetchall()
            
            for v_job in stale_v_jobs:
                v_job_id = v_job['v_job_id']
                retry_count = v_job['retry_count']
                
                if retry_count < 2:
                    logger.warning(f"Stale AWO Scan #{v_job_id} detected. Resetting to pending.")
                    cur.execute("""
                        UPDATE tb_verification_jobs 
                        SET status = 'pending', retry_count = retry_count + 1, updated_at = CURRENT_TIMESTAMP 
                        WHERE v_job_id = %s
                    """, (v_job_id,))
                else:
                    logger.error(f"Stale AWO Scan #{v_job_id} exceeded max retries. Marking as failed.")
                    cur.execute("""
                        UPDATE tb_verification_jobs 
                        SET status = 'failed', updated_at = CURRENT_TIMESTAMP 
                        WHERE v_job_id = %s
                    """, (v_job_id,))

    except Exception as e:
        logger.error(f"Error in recover_stale_jobs: {e}")

def update_persistent_metrics():
    """
    DB 현황을 기반으로 주요 메트릭을 영속적으로 기록 및 노출
    """
    try:
        from src.db.connection import get_db_cursor
        from src.utils.metrics import NSENTI_TOTAL_URLS, NSENTI_TOTAL_CONTENT, NSENTI_TOTAL_ERRORS
        
        with get_db_cursor() as cur:
            # 1. URL 총합
            cur.execute("SELECT COUNT(*) FROM tb_news_url")
            url_count = cur.fetchone()['count']
            NSENTI_TOTAL_URLS.set(url_count)
            
            # 2. 본문 총합
            cur.execute("SELECT COUNT(*) FROM tb_news_content")
            content_count = cur.fetchone()['count']
            NSENTI_TOTAL_CONTENT.set(content_count)
            
            # 3. 에러 총합
            cur.execute("SELECT COUNT(*) FROM tb_news_errors")
            error_count = cur.fetchone()['count']
            NSENTI_TOTAL_ERRORS.set(error_count)
            
            logger.info(f"Database Stats Synchronized: URLs={url_count}, Content={content_count}, Errors={error_count}")
            
    except Exception as e:
        logger.error(f"Error updating persistent metrics: {e}")

def main():
    logger.info("N-SentiTrader Scheduler started.")
    start_metrics_server()
    
    # 초기 동기화
    update_persistent_metrics()
    recover_stale_jobs()
    
    # 매일 오전 8시에 파이프라인 실행
    schedule.every().day.at("08:00").do(run_daily_pipeline)
    
    # 1분마다 즉시 실행 작업 확인
    schedule.every(1).minutes.do(check_immediate_tasks)
    
    # 5분마다 스테일 잡 회복 확인
    schedule.every(5).minutes.do(recover_stale_jobs)
    
    # 10분마다 영속 지표 동기화 로그
    schedule.every(10).minutes.do(update_persistent_metrics)
    
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()
