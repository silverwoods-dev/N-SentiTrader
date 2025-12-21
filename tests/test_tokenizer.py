# tests/test_tokenizer.py
import pytest
from unittest.mock import MagicMock, patch
import os

# We can't easily test the actual Mecab without it being installed,
# but we can test the FastAPI service logic if we mock MeCab.

@patch("mecab_ko.Tagger")
def test_tokenize_api(mock_tagger):
    from src.tokenizer_service import app
    from fastapi.testclient import TestClient
    
    # Mock Mecab node structure
    mock_node = MagicMock()
    mock_node.surface = "삼성전자"
    mock_node.feature = "NNP,*,F,삼성전자,*,*,*,*"
    mock_node.next = MagicMock()
    mock_node.next.surface = "상승"
    mock_node.next.feature = "NNG,*,T,상승,*,*,*,*"
    mock_node.next.next = None
    
    mock_tagger.return_value.parseToNode.return_value = mock_node
    
    client = TestClient(app)
    response = client.post("/tokenize", json={"text": "삼성전자 상승"})
    
    assert response.status_code == 200
    assert response.json() == {"tokens": ["삼성전자", "상승"]}
