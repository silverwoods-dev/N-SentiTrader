import pytest
from unittest.mock import MagicMock, patch
from src.collector.news import AddressCollector, BodyCollector, JobManager
from src.learner.lasso import LassoLearner
from src.predictor.scoring import Predictor
from datetime import datetime

@patch('src.db.connection.get_db_connection')
@patch('src.utils.mq.pika.BlockingConnection')
def test_full_pipeline_integration(mock_pika, mock_db):
    # 1. Setup Mocks
    mock_conn = MagicMock()
    mock_db.return_value.__enter__.return_value = mock_conn
    mock_cursor = mock_conn.cursor.return_value.__enter__.return_value
    
    # Mock tb_news_url check (return empty to allow insertion)
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = [
        {
            "content": "삼성전자 상승", 
            "excess_return": 0.02, 
            "date": datetime(2025, 12, 11).date(), 
            "published_at": datetime(2025, 12, 10)
        }
    ]
    
    # 2. Address Collection
    collector = AddressCollector()
    # Mock requests.get to return a fake news list page
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = '<a href="/news/123">News 1</a>'
        urls = collector.extract_urls(mock_get.return_value.text, "https://news.naver.com")
        collector.process_urls(urls)
    
    # Verify URL was published to MQ
    assert mock_pika.return_value.channel.return_value.basic_publish.called

    # 3. Body Collection (Consumer)
    body_collector = BodyCollector()
    # Mock the callback
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = '<div id="dic_area">삼성전자 주가 상승 본문</div>'
        
        # Simulate receiving a message
        method = MagicMock()
        properties = MagicMock()
        body = b'{"url": "https://n.news.naver.com/news/123", "url_hash": "abc", "stock_code": "005930", "news_date": "2025-12-17"}'
        body_collector.handle_message(None, method, properties, body)
    
    # Verify content was saved to DB
    assert mock_cursor.execute.called

    # 4. Learning (Lasso)
    with patch('polars.read_database') as mock_pl_read:
        import polars as pl
        # Mock data for training
        mock_pl_read.return_value = pl.DataFrame({
            "news_date": [datetime(2025, 12, 10)],
            "content": ["삼성전자 상승"],
            "excess_return": [0.02],
            "weight": [1.0]
        })
        
        learner = LassoLearner()
        learner.run_training()
        
    # Verify sentiment dict was saved
    assert mock_cursor.execute.called

    # 5. Prediction
    # Mock load_dict (fetchone/fetchall)
    # Since load_dict uses get_db_cursor, it will use our mock_cursor
    # We need to make sure it returns something for Main and Buffer
    mock_cursor.fetchall.side_effect = [
        [{"stock_code": "005930", "content": "삼성전자 상승"}], # Today's news
        [{"word": "삼성전자", "beta": 0.1}, {"word": "상승", "beta": 0.2}], # Main dict
        [] # Buffer dict
    ]
    
    predictor = Predictor()
    results = predictor.run_daily_prediction("20251217")
    
    assert len(results) > 0
    assert results[0]['stock_code'] == "005930"
    assert results[0]['total_score'] > 0
