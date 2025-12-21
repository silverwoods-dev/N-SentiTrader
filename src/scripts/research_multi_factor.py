
import sys
import os
import numpy as np
from datetime import datetime, timedelta
import polars as pl
from sklearn.metrics import mean_squared_error, mean_absolute_error

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.learner.lasso import LassoLearner

def run_experiment(stock_code, use_fundamentals):
    print(f"\n>>> Running Experiment for {stock_code} (Fundamentals: {use_fundamentals})")
    
    # 1 year period
    end_date = datetime.now().date().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    
    learner = LassoLearner(use_fundamentals=use_fundamentals)
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
    
    # Train
    learner.train(df_train, stock_code)
    
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
    
    # 1. Baseline (Text Only)
    res_base = run_experiment(stock, False)
    
    # 2. Hybrid (Text + Fundamentals)
    res_hybrid = run_experiment(stock, True)
    
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
