# src/learner/mlx_lasso.py
"""
MLX-based Lasso Solver using FISTA (Fast Iterative Soft-Thresholding Algorithm).
Optimized for Apple Silicon GPU via Unified Memory.
"""
import mlx.core as mx
import numpy as np
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def soft_threshold(x: mx.array, alpha: float) -> mx.array:
    """
    Proximal operator for L1 regularization (Soft Thresholding).
    S_alpha(x) = sign(x) * max(|x| - alpha, 0)
    """
    return mx.sign(x) * mx.maximum(mx.abs(x) - alpha, 0)


class MLXLasso:
    """
    Lasso regression solver using FISTA algorithm on MLX (Apple Silicon GPU).
    
    Minimizes: 0.5 * ||X @ w - y||^2 / n_samples + alpha * ||w||_1
    
    Parameters
    ----------
    alpha : float, default=1e-4
        Regularization strength (L1 penalty).
    max_iter : int, default=1000
        Maximum number of iterations.
    tol : float, default=1e-4
        Tolerance for convergence.
    verbose : bool, default=False
        Print convergence progress.
    """
    
    def __init__(
        self,
        alpha: float = 1e-4,
        max_iter: int = 1000,
        tol: float = 1e-4,
        verbose: bool = False
    ):
        self.alpha = alpha
        self.max_iter = max_iter
        self.tol = tol
        self.verbose = verbose
        self.coef_: Optional[np.ndarray] = None
        self.n_iter_: int = 0
        self.intercept_: float = 0.0
    
    def fit(self, X, y):
        """
        Fit the Lasso model using FISTA algorithm.
        
        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Training data (can be sparse scipy matrix or dense numpy array).
        y : array-like of shape (n_samples,)
            Target values.
        
        Returns
        -------
        self : object
            Fitted estimator.
        """
        # Convert to dense numpy if sparse
        if hasattr(X, 'toarray'):
            X_np = X.toarray().astype(np.float32)
        else:
            X_np = np.asarray(X, dtype=np.float32)
        
        y_np = np.asarray(y, dtype=np.float32).ravel()
        
        n_samples, n_features = X_np.shape
        
        # Convert to MLX arrays
        X_mlx = mx.array(X_np)
        y_mlx = mx.array(y_np)
        
        # Compute Lipschitz constant for step size
        # L = largest eigenvalue of X.T @ X / n_samples
        # Use power iteration to estimate spectral norm (memory efficient)
        if n_features > 20000:
            # Power iteration for large matrices (avoid X.T @ X allocation)
            v = mx.ones((n_features,)) / np.sqrt(n_features)
            for _ in range(10):  # 10 iterations usually sufficient
                Xv = X_mlx @ v
                XtXv = X_mlx.T @ Xv
                v = XtXv / (mx.linalg.norm(XtXv) + 1e-10)
                mx.eval(v)
            L = float(mx.linalg.norm(X_mlx @ v).item() ** 2) / n_samples
        else:
            # Direct computation for smaller matrices
            XtX = X_mlx.T @ X_mlx
            L = float(mx.trace(XtX).item()) / n_samples
            del XtX  # Free memory
        
        if L < 1e-10:
            L = 1.0  # Fallback for degenerate cases
        
        step_size = 1.0 / L
        
        if self.verbose:
            logger.info(f"[MLX FISTA] L={L:.4f}, step_size={step_size:.6f}, alpha={self.alpha}")
        
        # FISTA initialization
        w = mx.zeros((n_features,))
        w_old = mx.zeros((n_features,))
        t = 1.0
        
        # Precompute X.T @ y for gradient
        Xty = X_mlx.T @ y_mlx / n_samples
        
        for k in range(self.max_iter):
            # Momentum term (FISTA acceleration)
            z = w + ((t - 1) / (t + 1)) * (w - w_old)
            
            # Gradient step: grad = (X.T @ (X @ z) - X.T @ y) / n_samples
            grad = (X_mlx.T @ (X_mlx @ z)) / n_samples - Xty
            w_half = z - step_size * grad
            
            # Proximal step (Soft thresholding)
            w_new = soft_threshold(w_half, self.alpha * step_size)
            
            # Convergence check
            diff = mx.max(mx.abs(w_new - w)).item()
            
            # Update for next iteration
            w_old = w
            w = w_new
            t_new = (1 + np.sqrt(1 + 4 * t * t)) / 2
            t = t_new
            
            # Evaluate to ensure computation happens
            mx.eval(w)
            
            if diff < self.tol:
                if self.verbose:
                    logger.info(f"[MLX FISTA] Converged at iteration {k+1}, diff={diff:.2e}")
                break
            
            if self.verbose and (k + 1) % 100 == 0:
                residual = 0.5 * mx.mean(mx.square(X_mlx @ w - y_mlx)).item()
                l1_norm = mx.sum(mx.abs(w)).item()
                loss = residual + self.alpha * l1_norm
                logger.info(f"[MLX FISTA] Iter {k+1}: loss={loss:.6f}, diff={diff:.2e}")
        
        self.n_iter_ = k + 1
        
        # Convert back to numpy
        self.coef_ = np.array(w.tolist(), dtype=np.float64)
        
        if self.verbose:
            non_zero = np.count_nonzero(self.coef_)
            logger.info(f"[MLX FISTA] Finished: {self.n_iter_} iters, {non_zero} non-zero coefficients")
        
        return self
    
    def predict(self, X) -> np.ndarray:
        """Predict using the fitted model."""
        if self.coef_ is None:
            raise ValueError("Model not fitted. Call fit() first.")
        
        if hasattr(X, 'toarray'):
            X_np = X.toarray()
        else:
            X_np = np.asarray(X)
        
        return X_np @ self.coef_ + self.intercept_


class MLXLassoCV:
    """
    Lasso with Cross-Validation for alpha selection using MLX.
    
    Parameters
    ----------
    alphas : array-like, optional
        List of alphas to try. If None, uses logarithmic range.
    cv : int, default=5
        Number of cross-validation folds.
    max_iter : int, default=1000
        Maximum iterations for each FISTA run.
    """
    
    def __init__(
        self,
        alphas: Optional[list] = None,
        cv: int = 5,
        max_iter: int = 1000,
        tol: float = 1e-4,
        verbose: bool = False
    ):
        self.alphas = alphas or [1e-5, 5e-5, 1e-4, 5e-4, 1e-3, 5e-3]
        self.cv = cv
        self.max_iter = max_iter
        self.tol = tol
        self.verbose = verbose
        self.alpha_: Optional[float] = None
        self.coef_: Optional[np.ndarray] = None
        self.intercept_: float = 0.0
    
    def fit(self, X, y):
        """
        Fit with cross-validation to select the best alpha.
        """
        from sklearn.model_selection import KFold
        
        if hasattr(X, 'toarray'):
            X_np = X.toarray().astype(np.float32)
        else:
            X_np = np.asarray(X, dtype=np.float32)
        
        y_np = np.asarray(y, dtype=np.float32).ravel()
        
        n_samples = X_np.shape[0]
        kf = KFold(n_splits=self.cv, shuffle=True, random_state=42)
        
        best_alpha = self.alphas[0]
        best_score = -np.inf
        
        for alpha in self.alphas:
            scores = []
            
            for train_idx, val_idx in kf.split(X_np):
                X_train, X_val = X_np[train_idx], X_np[val_idx]
                y_train, y_val = y_np[train_idx], y_np[val_idx]
                
                model = MLXLasso(alpha=alpha, max_iter=self.max_iter, tol=self.tol, verbose=False)
                model.fit(X_train, y_train)
                
                # Score: negative MSE (higher is better)
                y_pred = model.predict(X_val)
                mse = np.mean((y_pred - y_val) ** 2)
                scores.append(-mse)
            
            mean_score = np.mean(scores)
            
            if self.verbose:
                logger.info(f"[MLX LassoCV] alpha={alpha:.2e}, mean_score={mean_score:.6f}")
            
            if mean_score > best_score:
                best_score = mean_score
                best_alpha = alpha
        
        self.alpha_ = best_alpha
        
        if self.verbose:
            logger.info(f"[MLX LassoCV] Best alpha: {self.alpha_:.2e}")
        
        # Refit on full data with best alpha
        final_model = MLXLasso(alpha=self.alpha_, max_iter=self.max_iter, tol=self.tol, verbose=self.verbose)
        final_model.fit(X_np, y_np)
        
        self.coef_ = final_model.coef_
        self.n_iter_ = final_model.n_iter_
        
        return self
    
    def predict(self, X) -> np.ndarray:
        if self.coef_ is None:
            raise ValueError("Model not fitted.")
        
        if hasattr(X, 'toarray'):
            X_np = X.toarray()
        else:
            X_np = np.asarray(X)
        
        return X_np @ self.coef_ + self.intercept_


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    # Generate synthetic data
    np.random.seed(42)
    n, p = 100, 500
    X = np.random.randn(n, p).astype(np.float32)
    true_coef = np.zeros(p)
    true_coef[:10] = np.random.randn(10)
    y = X @ true_coef + 0.1 * np.random.randn(n)
    
    # Fit MLXLasso
    model = MLXLasso(alpha=0.01, max_iter=500, verbose=True)
    model.fit(X, y)
    
    print(f"Non-zero coefficients: {np.count_nonzero(model.coef_)}")
    print(f"Iterations: {model.n_iter_}")
