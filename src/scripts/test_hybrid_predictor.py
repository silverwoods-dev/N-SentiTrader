#!/usr/bin/env python3
"""
Hybrid Predictor Test - TF-IDF + BERT Ensemble
Walk-Forward 검증 없이 기본 기능 테스트
"""
import sys
import time
import logging

sys.path.insert(0, '/Users/dev/CODE/N-SentiTrader')
logging.basicConfig(level=logging.INFO)

def test_hybrid_predictor():
    """HybridPredictor 기본 테스트"""
    print("="*60)
    print("Hybrid Predictor Test - TF-IDF + BERT Ensemble")
    print("="*60)
    
    from src.learner.hybrid_predictor import HybridPredictor
    
    # Initialize
    print("\n[1/3] Initializing HybridPredictor...")
    predictor = HybridPredictor(
        tfidf_weight=0.6,
        bert_weight=0.4,
        use_mlx=True
    )
    
    print(f"   TF-IDF weight: {predictor.tfidf_weight}")
    print(f"   BERT weight: {predictor.bert_weight}")
    print(f"   MLX enabled: {predictor.use_mlx}")
    
    # Test BERT embedder loading
    print("\n[2/3] Testing BERT Embedder...")
    start = time.time()
    
    test_texts = [
        "삼성전자 실적 호조로 주가 상승 예상",
        "LG화학 적자 전환 충격으로 투자심리 위축",
        "현대차 전기차 판매 신기록 달성"
    ]
    
    try:
        embeddings = predictor.bert_embedder.encode(test_texts)
        elapsed = time.time() - start
        
        print(f"   ✅ BERT embeddings generated")
        print(f"   Shape: {embeddings.shape}")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Using MLX: {predictor.bert_embedder.use_mlx}")
        
    except Exception as e:
        print(f"   ❌ BERT embedder error: {e}")
        return False
    
    # Test TF-IDF Learner
    print("\n[3/3] Testing TF-IDF Learner...")
    
    try:
        learner = predictor.tfidf_learner
        print(f"   ✅ TF-IDF Learner initialized")
        print(f"   n-gram: {learner.n_gram}")
        print(f"   lags: {learner.lags}")
        print(f"   decay_rate: {learner.decay_rate}")
        print(f"   max_features: {learner.max_features}")
        
    except Exception as e:
        print(f"   ❌ TF-IDF Learner error: {e}")
        return False
    
    print("\n" + "="*60)
    print("✅ Hybrid Predictor Test PASSED")
    print("="*60)
    print("\nComponents ready for Walk-Forward validation:")
    print("  - TF-IDF Lasso: n-gram=3, lag=5, decay='auto'")
    print("  - BERT Ridge: KR-FinBert embeddings")
    print("  - Ensemble: 60% TF-IDF + 40% BERT")
    
    return True


if __name__ == "__main__":
    success = test_hybrid_predictor()
    sys.exit(0 if success else 1)
