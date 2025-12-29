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
from src.utils.mq import publish_job, publish_verification_job
from src.utils.monitor import SystemWatchdog, persist_health_status
from src.nlp.dic_builder import DicBuilder

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_dictionary_sync():
    """
    MeCab 사용자 사전 및 종목 별칭 맵 동기화
    """
    logger.info("Starting MeCab dictionary and stock alias sync...")
    try:
        builder = DicBuilder()
        builder.sync_all()
        logger.info("MeCab dictionary and stock alias sync completed.")
    except Exception as e:
        logger.error(f"Error in dictionary sync: {e}")

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
            # Sequential training in scheduler blocks everything. Move to verification worker.
            publish_verification_job({
                "v_type": "DAILY_UPDATE",
                "stock_code": stock_code
            })
            logger.info(f"Enqueued daily buffer update for {stock_code}")
        
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
                AND updated_at < NOW() - INTERVAL '60 minutes'
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
                AND updated_at < NOW() - INTERVAL '60 minutes'
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
        from src.utils.metrics import (
            NSENTI_TOTAL_URLS, NSENTI_TOTAL_CONTENT, NSENTI_TOTAL_ERRORS, 
            QUEUE_DEPTH, QUEUE_MESSAGES_READY, QUEUE_MESSAGES_UNACKED
        )
        from src.utils.mq import get_queue_depths
        
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
            
            # 4. Queue Depths
            queue_depths = get_queue_depths()
            for q_name, details in queue_depths.items():
                QUEUE_DEPTH.labels(queue_name=q_name).set(details['total'])
                QUEUE_MESSAGES_READY.labels(queue_name=q_name).set(details['ready'])
                QUEUE_MESSAGES_UNACKED.labels(queue_name=q_name).set(details['unacked'])
            
            logger.info(f"Database Stats Synchronized: URLs={url_count}, Content={content_count}, Errors={error_count} | Queues={len(queue_depths)}")
            
    except Exception as e:
        logger.error(f"Error updating persistent metrics: {e}")

def run_watchdog():
    """
    Run System Watchdog to detect zombie workers and health issues
    """
    try:
        dog = SystemWatchdog()
        status = dog.check_health()
        persist_health_status(status)
        
        if status["status"] != "healthy":
            logger.warning(f"Watchdog Alert: {status['issues']}")
            
    except Exception as e:
        logger.error(f"Error running watchdog: {e}")


def run_financial_pipeline():
    """
    매일 장 마감 후 재무 데이터 수집 및 일일 성과(Actual Alpha) 확정
    """
    logger.info("Starting financial and settlement pipeline...")
    from src.collectors.fundamentals_collector import FundamentalsCollector
    from src.collectors.price_collector import PriceCollector
    from src.collectors.disclosure_collector import DisclosureCollector
    from src.db.connection import get_db_cursor
    
    try:
        f_collector = FundamentalsCollector()
        p_collector = PriceCollector()
        d_collector = DisclosureCollector()
        today_str = datetime.now().strftime('%Y%m%d')
        
        with get_db_cursor() as cur:
            cur.execute("SELECT stock_code FROM daily_targets WHERE status = 'active'")
            active_targets = cur.fetchall()
            
        for target in active_targets:
            stock_code = target['stock_code']
            # 1. 재무 데이터 수집
            f_collector.collect(stock_code, today_str, today_str)
            
            # 2. 공시 데이터 수집 (DART)
            d_collector.collect(stock_code, today_str, today_str)

            # 3. 주가 및 알파 확정 (당일자 예측분에 대해 실현 여부 기록)
            p_collector.collect_and_settle(stock_code, today_str)
            
        logger.info("Financial and settlement pipeline completed.")
        
    except Exception as e:
        logger.error(f"Error in financial pipeline: {e}")

def run_awo_optimization():
    """매주 활성 종목들에 대해 AWO 전수 스캔 및 최적 모델 승격 수행"""
    logger.info("Starting weekly AWO optimization...")
    from src.db.connection import get_db_cursor
    
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT stock_code FROM daily_targets WHERE status = 'active'")
            active_targets = cur.fetchall()
            
        for target in active_targets:
            stock_code = target['stock_code']
            logger.info(f"Enqueuing AWO Scan Job for {stock_code}")
            
            # Create a pending entry in tb_verification_jobs so dashboard can see it
            v_job_id = None
            from src.db.connection import get_db_cursor
            with get_db_cursor() as cur:
                cur.execute("""
                    INSERT INTO tb_verification_jobs (stock_code, v_type, params, status)
                    VALUES (%s, 'AWO_SCAN', %s, 'pending')
                    RETURNING v_job_id
                """, (stock_code, json.dumps({"range": "1-11m", "val_months": 1})))
                v_job_id = cur.fetchone()['v_job_id']

            # Move execution to worker
            publish_verification_job({
                "v_type": "AWO_SCAN",
                "stock_code": stock_code,
                "v_job_id": v_job_id,
                "val_months": 1
            })
            logger.info(f"AWO Scan enqueued (Job #{v_job_id})")
            
        logger.info("Weekly AWO optimization completed.")
    except Exception as e:
        logger.error(f"Error in AWO optimization: {e}")

def run_drift_check():
    """매일 모델의 성과 드리프트를 감시하고 필요시 자동 롤백"""
    logger.info("Starting daily model drift check...")
    from src.learner.drift_monitor import DriftMonitor
    from src.db.connection import get_db_cursor
    
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT stock_code FROM daily_targets WHERE status = 'active'")
            active_targets = cur.fetchall()
            
        for target in active_targets:
            stock_code = target['stock_code']
            monitor = DriftMonitor(stock_code)
            monitor.check_drift_and_rollback()
            
        logger.info("Daily drift check completed.")
    except Exception as e:
        logger.error(f"Error in drift check: {e}")

def main():
    logger.info("N-SentiTrader Scheduler started.")
    start_metrics_server()
    
    # 초기 동기화
    run_dictionary_sync()
    update_persistent_metrics()
    recover_stale_jobs()
    
    # 매일 오전 2시에 MeCab 사전 및 종목 별칭 동기화
    schedule.every().day.at("02:00").do(run_dictionary_sync)
    
    # 매일 오전 8시에 파이프라인 실행 (뉴스 분석)
    schedule.every().day.at("08:00").do(run_daily_pipeline)
    
    # 매일 오후 4시에 재무 데이터 수집 및 알파 확정
    schedule.every().day.at("16:00").do(run_financial_pipeline)
    
    # 매일 오후 4시 30분에 드리프트 감시 (알파 확정 후)
    schedule.every().day.at("16:30").do(run_drift_check)
    
    # 매주 일요일 자정에 AWO 최적화 수행
    schedule.every().sunday.at("00:00").do(run_awo_optimization)
    
    # 1분마다 즉시 실행 작업 확인
    schedule.every(1).minutes.do(check_immediate_tasks)
    
    # 5분마다 스테일 잡 회복 확인
    schedule.every(5).minutes.do(recover_stale_jobs)
    
    # 30초마다 영속 지표 동기화 로그 (More Realtime)
    schedule.every(30).seconds.do(update_persistent_metrics)
    schedule.every(1).minutes.do(run_watchdog)
    
    while True:
        schedule.run_pending()
        time.sleep(10)

if __name__ == "__main__":
    main()
