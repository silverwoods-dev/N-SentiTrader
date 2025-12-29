
import sys
import os
import numpy as np
from datetime import datetime, timedelta
import polars as pl
from sklearn.metrics import mean_squared_error, mean_absolute_error

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.learner.lasso import LassoLearner
from src.db.connection import get_db_cursor
import random

def upsert_mock_fundamentals(stock_code):
    """ Inject mock fundamental data for the last year to ensure non-zero features. """
    print(f"\n>>> Injecting Mock Fundamentals for {stock_code}...")
    
    dates = [
        (datetime.now() - timedelta(days=360)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=270)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'),
        (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
        datetime.now().strftime('%Y-%m-%d')
    ]
    
    with get_db_cursor() as cur:
        for d in dates:
            # Generate random walk-ish data
            per = 10.0 + random.uniform(-2, 2)
            pbr = 1.3 + random.uniform(-0.2, 0.2)
            roe = 12.0 + random.uniform(-3, 3)
            cap = 400000000000000 + random.uniform(-10000000000000, 50000000000000)
            
            cur.execute("""
                INSERT INTO tb_stock_fundamentals (stock_code, base_date, per, pbr, roe, market_cap)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (stock_code, base_date) 
                DO UPDATE SET per=EXCLUDED.per, pbr=EXCLUDED.pbr, roe=EXCLUDED.roe, market_cap=EXCLUDED.market_cap
            """, (stock_code, d, per, pbr, roe, cap))
    print("    Done.")

def run_experiment(stock_code, use_fundamentals, alpha=0.005):
    print(f"\n>>> Running Experiment for {stock_code} (Fundamentals: {use_fundamentals}, Alpha: {alpha})")
    
    # 1 year period
    end_date = datetime.now().date().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    learner = LassoLearner(alpha=alpha, use_fundamentals=use_fundamentals)
    df_prices, df_news, df_fund = learner.fetch_data(stock_code, start_date, end_date)
    
    if df_prices is None or len(df_prices) < 20:
        print("Insufficient data.")
        return None
        
    df = learner.prepare_features(df_prices, df_news, df_fund)
    
    if len(df) < 20:
        print("Insufficient features DF.")
        return None
        
    # Split Train/Test (Last 20%)
    split_idx = int(len(df) * 0.8)
    df_train = df.head(split_idx)
    df_test = df.tail(len(df) - split_idx)
    
    print(f"    Train size: {len(df_train)}, Test size: {len(df_test)}")
    
    if use_fundamentals:
        dense_cols = ["per", "pbr", "roe", "log_market_cap"]
        print(f"    [Debug] Fundamentals Head:\n{df_fund.head(3)}")
        print(f"    [Debug] Fundamentals Train Std:\n{df_train.select(dense_cols).std()}")
        print(f"    [Debug] Fundamentals Train Mean:\n{df_train.select(dense_cols).mean()}")
        
    # Train
    learner.train(df_train, stock_code)
    
    if use_fundamentals:
        # Check coefficients for dense features (last 4)
        # However, coef_ corresponds to X_weighted which matches keep_indices.
        # keep_indices includes dense indices at the end.
        dense_coefs = learner.model.coef_[-4:]
        print(f"    [Debug] Dense Coefficients (PER, PBR, ROE, Cap): {dense_coefs}")
    
    # Predict
    y_true = df_test["excess_return"].cast(pl.Float64).to_numpy()
    y_pred = learner.predict(df_test)
    
    # Metrics
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    
    y_true_dir = (y_true > 0).astype(int)
    y_pred_dir = (y_pred > 0).astype(int)
    hit_rate = np.mean(y_true_dir == y_pred_dir)
    
    print(f"    [Result] RMSE: {rmse:.5f}, MAE: {mae:.5f}, Hit Rate: {hit_rate:.2%}")
    return {"rmse": rmse, "mae": mae, "hit_rate": hit_rate}

if __name__ == "__main__":
    stock = "005930"
    
    print("=== Multi-Factor Research Experiment ===")
    
    # Inject Mock Data first (Uncomment if needed for testing pipeline with mock data)
    # upsert_mock_fundamentals(stock)
    
    # 1. Baseline (Text Only)
    res_base = run_experiment(stock, False)
    
    # 2. Hybrid (Text + Fundamentals) - Relax Alpha to see if factors are picked up
    res_hybrid = run_experiment(stock, True, alpha=0.0001)
    
    if res_base and res_hybrid:
        print("\n=== Summary ===")
        print(f"Current Stock: {stock}")
        print(f"Baseline (Text Only) -> RMSE: {res_base['rmse']:.5f}, Hit Rate: {res_base['hit_rate']:.2%}")
        print(f"Hybrid (Multi-Factor) -> RMSE: {res_hybrid['rmse']:.5f}, Hit Rate: {res_hybrid['hit_rate']:.2%}")
        
        improv_rmse = (res_base['rmse'] - res_hybrid['rmse']) / res_base['rmse'] * 100
        improv_hit = res_hybrid['hit_rate'] - res_base['hit_rate']
        
        print(f"\nImprovement:")
        print(f"  RMSE Reduction: {improv_rmse:.2f}%")
        print(f"  Hit Rate Gain: {improv_hit * 100:.2f}pp")
