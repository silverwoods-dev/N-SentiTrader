# tests/test_predictor.py
import pytest
from unittest.mock import MagicMock, patch
from src.predictor.scoring import Predictor

@pytest.fixture
def predictor():
    return Predictor()

@patch("src.predictor.scoring.get_db_cursor")
def test_predict(mock_cursor, predictor):
    # Mock DB to return some sentiment words
    mock_cur = mock_cursor.return_value.__enter__.return_value
    mock_cur.fetchall.side_effect = [
        [{"word": "상승", "beta": 0.5}, {"word": "호재", "beta": 0.3}], # Main
        [{"word": "급등", "beta": 0.8}] # Buffer
    ]
    
    tokens = ["상승", "호재", "급등", "평범"]
    result = predictor.predict("005930", tokens, "v1")
    
    assert result["main_score"] == pytest.approx(0.8)
    assert result["buffer_score"] == pytest.approx(0.8)
    assert result["total_score"] == pytest.approx(1.6)
    assert result["prediction"] == 1
