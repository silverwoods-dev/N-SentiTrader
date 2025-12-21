# tests/test_collector_body.py
import pytest
from unittest.mock import MagicMock, patch
from src.collector.news import BodyCollector

@pytest.fixture
def collector():
    return BodyCollector()

def test_extract_content(collector):
    html = """
    <html>
        <body>
            <h1 class="title">News Title</h1>
            <div class="content">This is the news content.</div>
            <span class="date">2025-12-18 10:00:00</span>
        </body>
    </html>
    """
    # Note: Extraction logic will depend on the actual site structure.
    # For now, we'll use a generic mockable structure.
    data = collector.extract_content(html)
    assert data["title"] == "News Title"
    assert data["content"] == "This is the news content."
    assert data["published_at"] == "2025-12-18 10:00:00"

@patch("src.collector.news.get_db_cursor")
@patch("src.collector.news.requests.get")
def test_handle_message(mock_get, mock_cursor, collector):
    mock_response = MagicMock()
    mock_response.text = "<html><h1 class='title'>Title</h1><div class='content'>Content</div><span class='date'>2025-12-18</span></html>"
    mock_get.return_value = mock_response
    
    mock_cur = mock_cursor.return_value.__enter__.return_value
    
    message = {"url": "https://news.naver.com/news/123", "url_hash": "hash123"}
    collector.handle_message(None, None, None, message)
    
    # Check if DB insert was called
    assert mock_cur.execute.call_count >= 2 # One for update status, one for insert content
