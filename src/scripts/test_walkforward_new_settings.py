#!/usr/bin/env python3
"""
Walk-Forward Validation Test with New Settings
n-gram=3, lag=5, decay='auto' 설정 검증
"""
import sys
import time
import logging

sys.path.insert(0, '/app')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_walkforward_new_settings():
    """새 설정으로 Walk-Forward 검증 실행 (짧은 기간)"""
    from src.learner.validator import WalkForwardValidator
    from src.learner.lasso import LassoLearner
    
    logger.info("="*60)
    logger.info("Walk-Forward Validation Test - New Settings")
    logger.info("="*60)
    
    # 새 설정 확인 (LassoLearner의 기본값 확인)
    learner_check = LassoLearner()
    logger.info(f"[Settings] n_gram={learner_check.n_gram}, lags={learner_check.lags}, decay_rate={learner_check.decay_rate}")
    logger.info(f"[Settings] max_features={learner_check.max_features}, min_df={learner_check.min_df}")
    
    # Walk-Forward 검증 (짧은 기간)
    # WalkForwardValidator가 내부적으로 LassoLearner를 생성 (새 기본값 사용)
    validator = WalkForwardValidator(
        stock_code="005930",
        use_sector_beta=False
    )
    
    # 30일 검증 (빠른 테스트)
    start_date = "2025-11-01"
    end_date = "2025-11-30"
    train_days = 60
    
    logger.info(f"\n[Test] Period: {start_date} ~ {end_date}")
    logger.info(f"[Test] Train days: {train_days}")
    
    start_time = time.time()
    
    try:
        result = validator.run_validation(
            start_date=start_date,
            end_date=end_date,
            train_days=train_days,
            retrain_frequency='weekly'
        )
        
        elapsed = time.time() - start_time
        
        logger.info("\n" + "="*60)
        logger.info("WALK-FORWARD VALIDATION RESULTS")
        logger.info("="*60)
        logger.info(f"Hit Rate:     {result.get('hit_rate', 0)*100:.1f}%")
        logger.info(f"MAE:          {result.get('mae', 0):.4f}")
        logger.info(f"Total Days:   {result.get('total_days', 0)}")
        logger.info(f"Elapsed Time: {elapsed:.1f}s")
        logger.info("="*60)
        
        return result
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = test_walkforward_new_settings()
    sys.exit(0 if result else 1)
