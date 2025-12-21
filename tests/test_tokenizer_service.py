import pytest
from fastapi.testclient import TestClient
from src.tokenizer_service import app

client = TestClient(app)

def test_tokenize():
    response = client.post("/tokenize", json={"text": "삼성전자의 주가가 상승하고 있습니다."})
    assert response.status_code == 200
    tokens = response.json()["tokens"]
    assert "삼성전자" in tokens
    assert "주가" in tokens
    assert "상승" in tokens

def test_tokenize_empty():
    response = client.post("/tokenize", json={"text": ""})
    assert response.status_code == 200
    assert response.json()["tokens"] == []
