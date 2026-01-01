#!/usr/bin/env python3
"""
MLX Local Benchmark - Apple Metal GPU Test
실제 MLX 가속 성능 테스트 (Docker 외부)
"""
import time
import sys
import gc
import numpy as np

sys.path.insert(0, '/Users/dev/CODE/N-SentiTrader')

# Check MLX availability
try:
    import mlx.core as mx
    print(f"✅ MLX {mx.__version__} available")
    print(f"   Default device: {mx.default_device()}")
    MLX_AVAILABLE = True
except ImportError as e:
    print(f"❌ MLX not available: {e}")
    MLX_AVAILABLE = False

def benchmark_mlx_lasso():
    """MLX Lasso 벤치마크"""
    if not MLX_AVAILABLE:
        print("MLX not available, skipping benchmark")
        return
    
    print("\n" + "="*60)
    print("MLX Lasso Benchmark - Apple Metal GPU")
    print("="*60)
    
    # 샘플 데이터 생성
    np.random.seed(42)
    n_samples = 10000
    n_features = 50000
    
    print(f"\nGenerating test data: {n_samples} samples x {n_features} features")
    
    # Sparse matrix (TF-IDF like)
    density = 0.01  # 1% non-zero
    X_np = np.zeros((n_samples, n_features), dtype=np.float32)
    for i in range(n_samples):
        non_zero_idx = np.random.choice(n_features, size=int(n_features * density), replace=False)
        X_np[i, non_zero_idx] = np.random.rand(len(non_zero_idx))
    
    y_np = np.random.randn(n_samples).astype(np.float32)
    
    print(f"Data shape: X={X_np.shape}, y={y_np.shape}")
    print(f"Memory: {X_np.nbytes / 1024 / 1024:.1f} MB")
    
    # Convert to MLX arrays
    X_mlx = mx.array(X_np)
    y_mlx = mx.array(y_np)
    
    # Simple Lasso-like computation (coordinate descent step simulation)
    print("\nRunning MLX matrix operations...")
    
    start = time.time()
    
    # Simulate Lasso computation
    for _ in range(5):
        # XtX approximation
        XtX_diag = mx.sum(X_mlx ** 2, axis=0)
        # Xty
        Xty = mx.matmul(X_mlx.T, y_mlx[:, None])
        # Soft threshold (Lasso step)
        alpha = 0.0001
        w = mx.sign(Xty) * mx.maximum(mx.abs(Xty) - alpha, 0) / (XtX_diag[:, None] + 1e-8)
        mx.eval(w)  # Force computation
    
    elapsed = time.time() - start
    
    print(f"\n✅ MLX computation completed")
    print(f"   Time: {elapsed:.3f}s (5 iterations)")
    print(f"   Per iteration: {elapsed/5*1000:.1f}ms")
    print(f"   Non-zero weights: {int(mx.sum(w != 0))}")
    
    return elapsed


def benchmark_numpy_baseline():
    """NumPy baseline comparison"""
    print("\n" + "="*60)
    print("NumPy Baseline (CPU)")
    print("="*60)
    
    np.random.seed(42)
    n_samples = 10000
    n_features = 50000
    
    print(f"\nGenerating test data: {n_samples} samples x {n_features} features")
    
    density = 0.01
    X_np = np.zeros((n_samples, n_features), dtype=np.float32)
    for i in range(n_samples):
        non_zero_idx = np.random.choice(n_features, size=int(n_features * density), replace=False)
        X_np[i, non_zero_idx] = np.random.rand(len(non_zero_idx))
    
    y_np = np.random.randn(n_samples).astype(np.float32)
    
    print("\nRunning NumPy matrix operations...")
    
    start = time.time()
    
    for _ in range(5):
        XtX_diag = np.sum(X_np ** 2, axis=0)
        Xty = X_np.T @ y_np[:, None]
        alpha = 0.0001
        w = np.sign(Xty) * np.maximum(np.abs(Xty) - alpha, 0) / (XtX_diag[:, None] + 1e-8)
    
    elapsed = time.time() - start
    
    print(f"\n✅ NumPy computation completed")
    print(f"   Time: {elapsed:.3f}s (5 iterations)")
    print(f"   Per iteration: {elapsed/5*1000:.1f}ms")
    
    return elapsed


if __name__ == "__main__":
    numpy_time = benchmark_numpy_baseline()
    mlx_time = benchmark_mlx_lasso()
    
    if mlx_time and numpy_time:
        speedup = numpy_time / mlx_time
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        print(f"NumPy (CPU):  {numpy_time:.3f}s")
        print(f"MLX (GPU):    {mlx_time:.3f}s")
        print(f"Speedup:      {speedup:.2f}x")
        print("="*60)
