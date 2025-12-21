# src/scripts/research_window_optimization.py
import logging
import pandas as pd
from datetime import datetime, timedelta
from src.learner.validator import WalkForwardValidator

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OptimizationResearch")

def main():
    stock_code = "005930" # 삼성전자
    v = WalkForwardValidator(stock_code)
    
    # 최근 5일만 테스트하여 연구 파이프라인 작동 검증 (Rapid Mode)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=5)
    
    # 대표적인 윈도우 범위 3가지만 선택 (1, 3, 6개월)
    test_ranges = [30, 90, 180]
    
    summary_results = []
    
    logger.info(f"=== Starting Optimization Research (Rapid Mode) for {stock_code} ===")
    logger.info(f"Test Period: {start_date} ~ {end_date}")
    
    for days in test_ranges:
        logger.info(f"--- Testing Window: {days} days ---")
        try:
            res = v.run_validation(
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d'),
                train_days=days,
                dry_run=True  # 연구용이므로 DB에 저장하지 않음
            )
            
            if res["total_days"] > 0:
                summary_results.append({
                    "train_window_days": days,
                    "hit_rate": res["hit_rate"],
                    "total_days": res["total_days"]
                })
                logger.info(f"Result for {days}d: Hit Rate = {res['hit_rate']:.2%}")
            else:
                logger.warning(f"No results for {days}d window. Check data density.")
                
        except Exception as e:
            logger.error(f"Error testing window {days}d: {e}")
            
    # 최종 결과 출력
    if summary_results:
        df = pd.DataFrame(summary_results)
        print("\n" + "="*60)
        print(" TRAINING WINDOW OPTIMIZATION RESULTS (SAMSUNG ELECTRONICS) ")
        print("="*60)
        print(df.to_string(index=False))
        print("="*60)
        
        best_row = df.loc[df['hit_rate'].idxmax()]
        print(f"\nRecommended Training Window: {best_row['train_window_days']} days (Hit Rate: {best_row['hit_rate']:.2%})")
        
        # Save Report to file for PRD Reference
        with open("research_output.txt", "w") as f:
            f.write(" TRAINING WINDOW OPTIMIZATION RESULTS (SAMSUNG ELECTRONICS) \n")
            f.write("="*60 + "\n")
            f.write(df.to_string(index=False) + "\n")
            f.write("="*60 + "\n")
            f.write(f"\nRecommended Training Window: {best_row['train_window_days']} days (Hit Rate: {best_row['hit_rate']:.2%})\n")
            
    else:
        print("No research results generated. Ensure news data is collected.")

if __name__ == "__main__":
    main()
