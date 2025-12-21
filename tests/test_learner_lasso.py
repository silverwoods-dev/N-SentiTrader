# tests/test_learner_lasso.py
import pytest
import numpy as np
from src.learner.lasso import LassoLearner

def test_lasso_train():
    learner = LassoLearner(alpha=0.001)
    texts = [
        "삼성전자 실적 호조 상승 기대",
        "삼성전자 실적 악화 하락 우려",
        "반도체 시장 호황 상승",
        "반도체 공급 과잉 하락"
    ]
    # Simple target: '상승' -> positive, '하락' -> negative
    y = np.array([1.0, -1.0, 1.0, -1.0])
    weights = np.array([1.0, 1.0, 0.5, 0.5]) # Older news has less weight
    
    sentiment_dict = learner.train(texts, y, weights=weights)
    
    assert len(sentiment_dict) > 0
    # '상승' should have positive beta, '하락' should have negative beta
    # (Note: Lasso might zero them out if alpha is too high, but with 0.001 it should be fine)
    assert sentiment_dict.get("상승", 0) > 0
    assert sentiment_dict.get("하락", 0) < 0
