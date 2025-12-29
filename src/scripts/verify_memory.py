
import logging
import psutil
import os
import time
from src.learner.lasso import LassoLearner

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_memory():
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024
    logger.info(f"[MEM] Current Memory: {mem_mb:.2f} MB")

def verify_memory_opt():
    stock_code = "005930" # Samsung
    end_date = "2025-12-30"
    start_date = "2025-06-30" # 6 months
    
    logger.info("Initializing LassoLearner...")
    # Use min_df=3 (default), min_relevance=10
    learner = LassoLearner(min_df=3, min_relevance=10)
    
    log_memory()
    logger.info(f"Fetching data for {stock_code} ({start_date} ~ {end_date})...")
    
    df_prices, df_news, df_fund = learner.fetch_data(stock_code, start_date, end_date)
    
    if df_news is None or df_news.is_empty():
        logger.error("No news fetched! Verification failed.")
        return

    logger.info(f"Fetched {len(df_news)} news items.")
    log_memory()
    
    logger.info("Preparing features (Tokenization)...")
    df = learner.prepare_features(df_prices, df_news, df_fund)
    log_memory()
    
    logger.info("Training (Vectorization with Generator)...")
    # We just run train and catch the output
    try:
        # Dry run train logic
        learner.train(df, stock_code=stock_code)
        logger.info("Training (Vectorization) completed successfully without OOM.")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        
    log_memory()

if __name__ == "__main__":
    verify_memory_opt()
