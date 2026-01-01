"""
KR-FinBERT Embedding Generator using MLX
Apple Silicon 최적화 한국어 금융 임베딩

Phase 3: N-SentiTrader Architecture Improvement
"""
import numpy as np
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Check MLX availability
try:
    import mlx.core as mx
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    logger.info("MLX not available, will use PyTorch/Transformers fallback")


class FinBERTEmbedder:
    """
    KR-FinBERT 기반 임베딩 생성기
    MLX (Apple Silicon) 또는 PyTorch fallback 지원
    """
    
    def __init__(self, model_path: str = "snunlp/KR-FinBert", use_mlx: bool = True):
        """
        Args:
            model_path: Hugging Face 모델 경로
            use_mlx: MLX 사용 여부 (False면 PyTorch 사용)
        """
        self.model_path = model_path
        self.use_mlx = use_mlx and MLX_AVAILABLE
        self.model = None
        self.tokenizer = None
        self._embedding_dim = 768  # BERT base
        self._is_loaded = False
        
    def _load_model(self):
        """모델 로드 (lazy loading)"""
        if self._is_loaded:
            return
            
        if self.use_mlx:
            self._load_mlx_model()
        else:
            self._load_torch_model()
            
        self._is_loaded = True
    
    def _load_mlx_model(self):
        """MLX 모델 로드"""
        try:
            from mlx_embeddings.models import load_model
            logger.info(f"Loading {self.model_path} with MLX...")
            self.model, self.tokenizer = load_model(self.model_path)
            logger.info("MLX model loaded successfully")
        except ImportError:
            logger.warning("mlx_embeddings not available, falling back to PyTorch")
            self.use_mlx = False
            self._load_torch_model()
        except Exception as e:
            logger.warning(f"MLX model load failed: {e}, falling back to PyTorch")
            self.use_mlx = False
            self._load_torch_model()
    
    def _load_torch_model(self):
        """PyTorch/Transformers 모델 로드 (fallback)"""
        try:
            from transformers import AutoModel, AutoTokenizer
            import torch
            
            logger.info(f"Loading {self.model_path} with PyTorch...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            self.model = AutoModel.from_pretrained(self.model_path)
            self.model.eval()
            
            # Use MPS if available (Apple Silicon)
            if torch.backends.mps.is_available():
                self.model = self.model.to("mps")
                self._device = "mps"
            else:
                self._device = "cpu"
                
            logger.info(f"PyTorch model loaded on {self._device}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        텍스트 리스트를 임베딩 벡터로 변환
        
        Args:
            texts: 텍스트 리스트
            batch_size: 배치 크기
            
        Returns:
            np.ndarray: (N, 768) 임베딩 행렬
        """
        self._load_model()
        
        if not texts:
            return np.zeros((0, self._embedding_dim))
        
        if self.use_mlx:
            return self._encode_mlx(texts, batch_size)
        else:
            return self._encode_torch(texts, batch_size)
    
    def _encode_mlx(self, texts: List[str], batch_size: int) -> np.ndarray:
        """MLX 임베딩 생성"""
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_emb = self.model.encode(batch)
            if hasattr(batch_emb, 'tolist'):
                batch_emb = np.array(batch_emb.tolist())
            embeddings.append(batch_emb)
        return np.vstack(embeddings)
    
    def _encode_torch(self, texts: List[str], batch_size: int) -> np.ndarray:
        """PyTorch 임베딩 생성"""
        import torch
        
        embeddings = []
        with torch.no_grad():
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i+batch_size]
                
                # Tokenize
                inputs = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                )
                
                # Move to device
                inputs = {k: v.to(self._device) for k, v in inputs.items()}
                
                # Get embeddings
                outputs = self.model(**inputs)
                
                # Use CLS token embedding
                cls_embeddings = outputs.last_hidden_state[:, 0, :]
                embeddings.append(cls_embeddings.cpu().numpy())
                
        return np.vstack(embeddings)
    
    def get_sentiment_features(self, texts: List[str]) -> np.ndarray:
        """
        감성 분석용 CLS 토큰 임베딩 추출
        (encode와 동일, 명시적 API)
        """
        return self.encode(texts)
    
    @property
    def embedding_dim(self) -> int:
        """임베딩 차원 반환"""
        return self._embedding_dim


# Convenience function
def get_embedder(model_path: str = "snunlp/KR-FinBert", use_mlx: bool = True) -> FinBERTEmbedder:
    """
    FinBERTEmbedder 인스턴스 생성
    
    Args:
        model_path: Hugging Face 모델 경로
        use_mlx: MLX 사용 여부
        
    Returns:
        FinBERTEmbedder 인스턴스
    """
    return FinBERTEmbedder(model_path=model_path, use_mlx=use_mlx)


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)
    
    embedder = FinBERTEmbedder()
    test_texts = [
        "삼성전자 실적 호조로 주가 상승 예상",
        "LG화학 적자 전환 충격",
        "현대차 전기차 판매 호조"
    ]
    
    embeddings = embedder.encode(test_texts)
    print(f"Embeddings shape: {embeddings.shape}")
    print(f"Using MLX: {embedder.use_mlx}")
