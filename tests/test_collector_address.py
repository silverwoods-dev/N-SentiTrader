# tests/test_collector_address.py
import pytest
from unittest.mock import MagicMock, patch
from src.collector.news import AddressCollector

@pytest.fixture
def collector():
    return AddressCollector()

def test_extract_urls(collector):
    # Mock HTML content
    html = """
    <html>
        <body>
            <a href="/news/123">News 1</a>
            <a href="/news/456">News 2</a>
            <a href="https://other.com/abc">External</a>
        </body>
    </html>
    """
    urls = collector.extract_urls(html, base_url="https://news.naver.com")
    assert "https://news.naver.com/news/123" in urls
    assert "https://news.naver.com/news/456" in urls
    assert len(urls) == 2

@patch("src.collector.news.get_db_cursor")
@patch("src.collector.news.publish_url")
def test_process_page(mock_publish, mock_cursor, collector):
    # Mock DB to return one existing URL
    mock_cur = mock_cursor.return_value.__enter__.return_value
    mock_cur.fetchone.side_effect = [True, False] # First URL exists, second doesn't
    
    urls = ["https://news.naver.com/news/123", "https://news.naver.com/news/456"]
    
    collector.process_urls(urls)
    
    # Should only publish the one that doesn't exist
    assert mock_publish.call_count == 1
    mock_publish.assert_called_once_with({
        "url": "https://news.naver.com/news/456",
        "url_hash": collector.get_url_hash("https://news.naver.com/news/456")
    })
