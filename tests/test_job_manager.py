# tests/test_job_manager.py
import pytest
from unittest.mock import MagicMock, patch
from src.collector.news import JobManager

@pytest.fixture
def manager():
    return JobManager()

@patch("src.collector.news.get_db_cursor")
def test_create_backfill_job(mock_cursor, manager):
    mock_cur = mock_cursor.return_value.__enter__.return_value
    
    manager.create_backfill_job(stock_code="005930", days=365)
    
    # Should insert into jobs and daily_targets
    assert mock_cur.execute.call_count >= 2
    # Check if daily_targets insert has 'paused' status
    calls = [call[0][0] for call in mock_cur.execute.call_args_list]
    assert any("INSERT INTO daily_targets" in s and "'paused'" in s for s in calls)
