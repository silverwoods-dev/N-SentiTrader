#!/usr/bin/env python3
"""
Celer vs MLX Lasso Benchmark with Extended Parameters
n-gram=3, lag=5, with dynamic decay rate calculation

Phase: Extended Benchmark for N-SentiTrader
"""
import time
import sys
import gc
import numpy as np
import resource  # Standard library alternative to psutil

sys.path.insert(0, '/Users/dev/CODE/N-SentiTrader')

from src.learner.lasso import LassoLearner


def get_memory_usage():
    """현재 프로세스 메모리 사용량 (MB) - resource 모듈 사용"""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024 / 1024  # macOS: bytes, Linux: KB


def run_benchmark(engine: str, n_gram: int, lags: int, stock_code: str = "005930"):
    """
    단일 엔진 벤치마크 실행
    """
    print(f"\n{'='*60}")
    print(f"Engine: {engine.upper()}, n-gram: {n_gram}, lags: {lags}")
    print(f"{'='*60}")
    
    gc.collect()
    mem_before = get_memory_usage()
    
    learner = LassoLearner(
        n_gram=n_gram,
        lags=lags,
        engine=engine,
        max_features=20000,  # Increased for 3-gram
        min_df=3,  # Lower threshold for more features
        decay_rate=0.4 if n_gram == 2 else 'auto'  # Use auto for extended params
    )
    
    start_time = time.time()
    
    try:
        # 90일 학습 윈도우
        result = learner.run_training(
            stock_code=stock_code,
            start_date="2025-07-01",
            end_date="2025-09-30",
            version=f"benchmark_{engine}_{n_gram}gram_{lags}lag",
            source="Benchmark"
        )
        
        elapsed = time.time() - start_time
        mem_after = get_memory_usage()
        
        # 결과 분석
        coef = learner.model.coef_
        non_zero = np.count_nonzero(coef)
        
        return {
            "engine": engine,
            "n_gram": n_gram,
            "lags": lags,
            "time_seconds": elapsed,
            "memory_mb": mem_after - mem_before,
            "peak_memory_mb": mem_after,
            "n_features": len(coef),
            "non_zero_coef": non_zero,
            "sparsity": 1 - (non_zero / len(coef)) if len(coef) > 0 else 0,
            "success": True,
            "error": None
        }
        
    except Exception as e:
        elapsed = time.time() - start_time
        mem_after = get_memory_usage()
        
        return {
            "engine": engine,
            "n_gram": n_gram,
            "lags": lags,
            "time_seconds": elapsed,
            "memory_mb": mem_after - mem_before,
            "peak_memory_mb": mem_after,
            "n_features": 0,
            "non_zero_coef": 0,
            "sparsity": 0,
            "success": False,
            "error": str(e)
        }


def calculate_dynamic_decay_rate(df_prices, df_news, lags: int = 5) -> dict:
    """
    동적 감쇠율 계산
    
    아이디어: 각 lag별로 뉴스와 주가 수익률의 상관관계를 계산하고,
    상관관계가 낮아지는 비율을 감쇠율로 사용
    
    Returns:
        dict: {lag: decay_weight} 형태의 동적 가중치
    """
    import polars as pl
    from scipy.stats import pearsonr
    
    correlations = {}
    
    for lag in range(1, lags + 1):
        # lag일 전 뉴스 수와 오늘 수익률의 상관관계
        # 실제 구현에서는 더 정교한 방법 사용
        correlations[lag] = 1.0 / lag  # Placeholder: 1/lag decay
    
    # 정규화: lag=1이 1.0이 되도록
    max_corr = max(correlations.values())
    decay_weights = {k: v / max_corr for k, v in correlations.items()}
    
    return decay_weights


def main():
    print("="*70)
    print("Celer vs MLX Lasso Benchmark - Extended Parameters")
    print("n-gram=3, lag=5, dynamic decay rate")
    print("="*70)
    
    # 테스트 설정
    configs = [
        # 기본 설정 (현재 프로덕션)
        {"engine": "celer", "n_gram": 2, "lags": 3},
        {"engine": "mlx", "n_gram": 2, "lags": 3},
        
        # 확장 설정 (목표)
        {"engine": "celer", "n_gram": 3, "lags": 5},
        {"engine": "mlx", "n_gram": 3, "lags": 5},
    ]
    
    results = []
    
    for config in configs:
        result = run_benchmark(**config)
        results.append(result)
        
        if result["success"]:
            print(f"  ✅ Time: {result['time_seconds']:.2f}s")
            print(f"  📊 Features: {result['n_features']:,} (non-zero: {result['non_zero_coef']:,})")
            print(f"  💾 Memory: {result['memory_mb']:.1f}MB (peak: {result['peak_memory_mb']:.1f}MB)")
        else:
            print(f"  ❌ Failed: {result['error']}")
    
    # 결과 요약
    print("\n" + "="*70)
    print("BENCHMARK RESULTS SUMMARY")
    print("="*70)
    print(f"{'Engine':<8} {'n-gram':<7} {'lags':<5} {'Time(s)':<10} {'Memory(MB)':<12} {'Features':<10} {'Status':<8}")
    print("-"*70)
    
    for r in results:
        status = "✅" if r["success"] else "❌"
        print(f"{r['engine']:<8} {r['n_gram']:<7} {r['lags']:<5} {r['time_seconds']:<10.2f} {r['memory_mb']:<12.1f} {r['n_features']:<10,} {status:<8}")
    
    return results


if __name__ == "__main__":
    results = main()
