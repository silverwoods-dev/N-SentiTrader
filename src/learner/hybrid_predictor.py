"""
Hybrid Ensemble Predictor
TF-IDF Lasso + KR-FinBERT 앙상블

Phase 4: N-SentiTrader Architecture Improvement
결합된 예측으로 Hit Rate 향상 목표
"""
import numpy as np
from typing import Dict, List, Optional, Any
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class HybridPredictor:
    """
    TF-IDF Lasso + KR-FinBERT Ridge 앙상블 예측기
    
    Architecture:
    - TF-IDF → Lasso → pred_1 (weight: 60%)
    - BERT → Ridge → pred_2 (weight: 40%)
    - Final = weighted average
    """
    
    def __init__(
        self,
        tfidf_weight: float = 0.6,
        bert_weight: float = 0.4,
        bert_model_path: str = "snunlp/KR-FinBert",
        use_mlx: bool = True
    ):
        """
        Args:
            tfidf_weight: TF-IDF Lasso 예측 가중치 (0.0 ~ 1.0)
            bert_weight: BERT Ridge 예측 가중치 (0.0 ~ 1.0)
            bert_model_path: Hugging Face BERT 모델 경로
            use_mlx: MLX 가속 사용 여부
        """
        assert abs(tfidf_weight + bert_weight - 1.0) < 1e-6, "Weights must sum to 1.0"
        
        self.tfidf_weight = tfidf_weight
        self.bert_weight = bert_weight
        self.bert_model_path = bert_model_path
        self.use_mlx = use_mlx
        
        # Models (lazy initialization)
        self._tfidf_learner = None
        self._bert_embedder = None
        self._bert_model = None
        self._bert_scaler = None
        
        self._is_trained = False
        self._stock_code = None
    
    @property
    def tfidf_learner(self):
        """Lazy load TF-IDF Lasso learner"""
        if self._tfidf_learner is None:
            from src.learner.lasso import LassoLearner
            self._tfidf_learner = LassoLearner()
        return self._tfidf_learner
    
    @property
    def bert_embedder(self):
        """Lazy load BERT embedder"""
        if self._bert_embedder is None:
            from src.learner.finbert_embedder import FinBERTEmbedder
            self._bert_embedder = FinBERTEmbedder(
                model_path=self.bert_model_path,
                use_mlx=self.use_mlx
            )
        return self._bert_embedder
    
    def train(
        self,
        df,  # polars DataFrame with 'tokens' and 'excess_return'
        stock_code: str,
        version: str = "hybrid_v1"
    ) -> Dict[str, Any]:
        """
        하이브리드 모델 학습
        
        Args:
            df: 학습 데이터 (tokens, excess_return 컬럼 필요)
            stock_code: 종목 코드
            version: 버전 태그
            
        Returns:
            학습 결과 딕셔너리
        """
        logger.info(f"Training Hybrid model for {stock_code}...")
        self._stock_code = stock_code
        
        # 1. TF-IDF Lasso 학습 (기존 로직)
        logger.info("  [1/2] Training TF-IDF Lasso...")
        tfidf_result = self.tfidf_learner.train(df, stock_code)
        
        # 2. BERT Embedding + Ridge 학습
        logger.info("  [2/2] Training BERT Ridge...")
        
        # 토큰 리스트 → 텍스트 (공백 join)
        if "tokens" in df.columns:
            texts = [" ".join(t) if isinstance(t, list) else str(t) 
                     for t in df["tokens"].to_list()]
        elif "content" in df.columns:
            texts = df["content"].to_list()
        else:
            raise ValueError("DataFrame must have 'tokens' or 'content' column")
        
        # BERT 임베딩 생성
        bert_features = self.bert_embedder.encode(texts)
        
        # 스케일링
        self._bert_scaler = StandardScaler()
        bert_features_scaled = self._bert_scaler.fit_transform(bert_features)
        
        # Ridge 학습
        y = df["excess_return"].cast(float).to_numpy()
        self._bert_model = Ridge(alpha=1.0)
        self._bert_model.fit(bert_features_scaled, y)
        
        self._is_trained = True
        
        logger.info(f"Hybrid model trained for {stock_code} (BERT dim: {bert_features.shape[1]})")
        
        return {
            "tfidf_result": tfidf_result,
            "bert_embedding_dim": bert_features.shape[1],
            "n_samples": len(y)
        }
    
    def predict(self, texts: List[str]) -> Dict[str, float]:
        """
        앙상블 예측 수행
        
        Args:
            texts: 뉴스 텍스트 리스트
            
        Returns:
            예측 결과 딕셔너리
        """
        if not self._is_trained:
            raise RuntimeError("Model not trained. Call train() first.")
        
        if not texts:
            return {"ensemble": 0.0, "tfidf": 0.0, "bert": 0.0}
        
        # 1. TF-IDF Lasso 예측
        # Note: Requires adapting LassoLearner.predict to handle raw texts
        # For now, we'll use a simplified approach
        tfidf_pred = 0.0  # Placeholder - needs integration
        
        # 2. BERT Ridge 예측
        bert_features = self.bert_embedder.encode(texts)
        bert_features_scaled = self._bert_scaler.transform(bert_features)
        bert_preds = self._bert_model.predict(bert_features_scaled)
        bert_pred = float(np.mean(bert_preds))
        
        # 3. 앙상블 결합
        ensemble_pred = (self.tfidf_weight * tfidf_pred) + (self.bert_weight * bert_pred)
        
        return {
            "ensemble": ensemble_pred,
            "tfidf": tfidf_pred,
            "bert": bert_pred
        }
    
    def predict_with_features(
        self,
        tfidf_features: np.ndarray,
        texts: List[str]
    ) -> Dict[str, float]:
        """
        피처가 이미 준비된 상태에서 예측
        
        Args:
            tfidf_features: TF-IDF 피처 행렬
            texts: BERT 임베딩용 텍스트
            
        Returns:
            예측 결과 딕셔너리
        """
        if not self._is_trained:
            raise RuntimeError("Model not trained. Call train() first.")
        
        # TF-IDF 예측
        tfidf_pred = float(self.tfidf_learner.model.predict(tfidf_features).mean())
        
        # BERT 예측
        bert_features = self.bert_embedder.encode(texts)
        bert_features_scaled = self._bert_scaler.transform(bert_features)
        bert_pred = float(self._bert_model.predict(bert_features_scaled).mean())
        
        # 앙상블
        ensemble_pred = (self.tfidf_weight * tfidf_pred) + (self.bert_weight * bert_pred)
        
        return {
            "ensemble": ensemble_pred,
            "tfidf": tfidf_pred,
            "bert": bert_pred,
            "direction": "up" if ensemble_pred > 0 else "down"
        }
    
    def get_bert_adjustment(self, texts: List[str]) -> float:
        """
        BERT 기반 알파 조정값 계산 (간단한 Hybrid 통합용)
        
        기존 TF-IDF 예측에 BERT 신호를 보조적으로 더하는 방식.
        
        Args:
            texts: 뉴스 텍스트 리스트
            
        Returns:
            BERT 기반 알파 조정값 (-0.05 ~ +0.05 범위로 클리핑)
        """
        if not texts:
            return 0.0
        
        try:
            # BERT 임베딩으로 감성 특징 추출
            sentiment_features = self.bert_embedder.get_sentiment_features(texts)
            
            # 평균 감성 점수 계산 (softmax 확률 기반)
            avg_pos = float(np.mean([f.get('positive', 0.5) for f in sentiment_features]))
            avg_neg = float(np.mean([f.get('negative', 0.5) for f in sentiment_features]))
            
            # 순 감성 점수
            net_sentiment = avg_pos - avg_neg
            
            # 알파 조정값으로 변환 (-0.05 ~ +0.05 범위)
            adjustment = np.clip(net_sentiment * 0.1, -0.05, 0.05)
            
            logger.debug(f"  [BERT] Adjustment: {adjustment:.4f} (pos={avg_pos:.2f}, neg={avg_neg:.2f})")
            return float(adjustment)
            
        except Exception as e:
            logger.warning(f"BERT adjustment failed: {e}")
            return 0.0


# Factory function for easy instantiation
def create_hybrid_predictor(
    tfidf_weight: float = 0.6,
    bert_weight: float = 0.4,
    use_mlx: bool = True
) -> HybridPredictor:
    """
    HybridPredictor 생성 팩토리
    
    Args:
        tfidf_weight: TF-IDF 가중치 (기본: 0.6)
        bert_weight: BERT 가중치 (기본: 0.4)
        use_mlx: MLX 사용 여부
        
    Returns:
        HybridPredictor 인스턴스
    """
    return HybridPredictor(
        tfidf_weight=tfidf_weight,
        bert_weight=bert_weight,
        use_mlx=use_mlx
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Test
    predictor = HybridPredictor()
    print(f"TF-IDF weight: {predictor.tfidf_weight}")
    print(f"BERT weight: {predictor.bert_weight}")
    print(f"MLX available: {predictor.use_mlx}")
