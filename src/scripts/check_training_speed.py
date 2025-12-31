import sys
import os
import time
import numpy as np
from datetime import datetime, timedelta

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.learner.lasso import LassoLearner

def test_training_speed(stock_code='005930', months=6):
    """
    Benchmarks Lasso training speed (Celer vs Sklearn).
    """
    print(f"Testing training speed for {stock_code} using {months} months of data...")
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=months*30)).strftime('%Y-%m-%d')
    
    learner = LassoLearner(use_cv_lasso=True)
    
    start_time = time.time()
    try:
        # 1. Fetch Data
        df_prices, df_news, df_fund = learner.fetch_data(stock_code, start_date, end_date)
        if df_prices is None or df_prices.is_empty():
            print("No data fetched.")
            return
            
        print(f"Data fetched: {len(df_prices)} price days, {len(df_news)} news items.")
        
        # 2. Prepare Features
        df = learner.prepare_features(df_prices, df_news, df_fund)
        print(f"Features prepared: {len(df)} rows.")
        
        # 3. Benchmark Training
        print("\nStarting Lasso training...")
        y_val = df["excess_return"].to_numpy()
        print(f"  Target variable (y) - Mean: {np.mean(y_val):.6f}, Std: {np.std(y_val):.6f}")
        
        train_start = time.time()
        sentiment_dict, scaler_params = learner.train(df, stock_code=stock_code)
        train_end = time.time()
        
        pure_train_time = train_end - train_start
        
        print(f"\n[Benchmark Results]")
        print(f"  Model Type: {type(learner.model)}")
        print(f"  Pure Training Time: {pure_train_time:.2f}s")
        if hasattr(learner.model, 'alpha_'):
             print(f"  Best Alpha from CV: {learner.model.alpha_}")
        
        non_zero = np.count_nonzero(learner.model.coef_)
        print(f"  Dictionary Size: {len(sentiment_dict)} words (Non-zero coefficients: {non_zero})")
        
        # 4. Print top keywords if any
        if sentiment_dict:
            sorted_dict = sorted(sentiment_dict.items(), key=lambda x: abs(x[1]), reverse=True)
            print("\nTop 5 Keywords:")
            for word, beta in sorted_dict[:5]:
                print(f"  {word}: {beta:.6f}")
        else:
            print("\nNote: No non-zero coefficients found for this specific dataset window.")
            
    except Exception as e:
        print(f"Error during training: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    test_training_speed()
