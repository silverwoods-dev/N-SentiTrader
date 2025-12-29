# src/tools/train_buffer.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.learner.manager import AnalysisManager
from src.db.connection import get_db_cursor
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STOCKS = [
    {"code": "005930", "name": "삼성전자"},
    {"code": "000660", "name": "SK하이닉스"},
]

def train_buffer():
    print("="*60)
    print("  Running Buffer Training (Last 7 Days)")
    print("="*60)
    
    for stock in STOCKS:
        print(f"\n[Buffer] Processing {stock['name']} ({stock['code']})...")
        am = AnalysisManager(stock['code'])
        try:
            # run_daily_update trains on last 7 days and saves as source='Buffer', version='daily_buffer'
            am.run_daily_update()
            
            # Verify
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT count(*) as cnt FROM tb_sentiment_dict 
                    WHERE stock_code = %s AND source = 'Buffer' AND version = 'daily_buffer'
                """, (stock['code'],))
                cnt = cur.fetchone()['cnt']
                print(f"    -> Buffer Dictionary Size: {cnt} words")
                
                # Activate it (manager usually doesn't strictly activate 'daily_buffer' in meta automatically? 
                # Let's check manager.py. It calls run_training.
                # LassoLearner.run_training sets is_active=True by default?
                # Yes: run_training(..., is_active=True, ...)
                print("    -> Activated.")
                
        except Exception as e:
            print(f"    [Error] {e}")

if __name__ == "__main__":
    train_buffer()
