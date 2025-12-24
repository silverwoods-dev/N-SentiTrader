# src/scripts/run_lasso_training.py
from src.learner.lasso import LassoLearner
from datetime import datetime, timedelta

def main():
    # 삼성전자 (005930)에 대해 최근 30일간의 데이터로 학습 시도
    stock_code = "005930"
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    
    print(f"Starting Lasso training for {stock_code} ({start_date} ~ {end_date})...")
    
    # alpha를 더 낮추어 테스트 (Lasso Path)
    alphas = [0.00001, 0.000001]
    
    for alpha in alphas:
        print(f"\n--- Trying Lasso with alpha={alpha} ---")
        learner = LassoLearner(alpha=alpha, n_gram=3, lags=5, min_df=1, use_cv_lasso=False)
        sentiment_dict = learner.run_training(stock_code, start_date, end_date, version=f"v1_test_a{alpha}")
        
        if sentiment_dict and len(sentiment_dict) > 0:
            print(f"Success! Found {len(sentiment_dict)} words.")
            break
        else:
            print("Zero words found. Retrying with lower alpha...")
    
    # learner 변수는 마지막 것을 유지 (출력용)
    
    if sentiment_dict:
        # 상위 10개 긍정 단어 출력 (값 큰 순)
        sorted_pos = sorted([(w, b) for w, b in sentiment_dict.items() if b is not None and b > 0], key=lambda x: x[1], reverse=True)
        print("\nTop 10 Positive Words:")
        for word, beta in sorted_pos[:10]:
            print(f"  {word}: {beta:.6f}")

        # 부정 단어는 가장 음수(부정 영향력 큰 것)부터 출력
        # (Lasso 특성상 0에 가까운 값이 -0.0으로 보일 수 있음 — 의미상 0과 동일)
        sorted_neg = sorted([(w, b) for w, b in sentiment_dict.items() if b is not None and b < 0], key=lambda x: x[1])
        print("\nTop 10 Negative Words:")
        for word, beta in sorted_neg[:10]:
            print(f"  {word}: {beta:.6f}")
    else:
        print("Training failed or insufficient data.")

if __name__ == "__main__":
    main()
