
import pytest
from fastapi.testclient import TestClient
from src.dashboard.app import app
from src.db.connection import get_db_cursor

client = TestClient(app)

def test_delete_target_api():
    stock_code = "TEST01"
    
    # 1. Setup: Ensure target exists
    with get_db_cursor() as cur:
        cur.execute("INSERT INTO tb_stock_master (stock_code, stock_name, market_type) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING", (stock_code, "Test Stock", "KOSPI"))
        cur.execute("INSERT INTO daily_targets (stock_code, status) VALUES (%s, %s) ON CONFLICT (stock_code) DO UPDATE SET status = 'active'", (stock_code, "active"))
    
    # 2. Delete the target
    response = client.delete(f"/targets/{stock_code}")
    # Before implementation, this should be 405 (Method Not Allowed) since it's not defined
    # Actually, if not defined at all, it's 404.
    assert response.status_code == 200
    
    # 3. Verify in DB
    with get_db_cursor() as cur:
        cur.execute("SELECT * FROM daily_targets WHERE stock_code = %s", (stock_code,))
        row = cur.fetchone()
        assert row is None
        
        # Cleanup master
        cur.execute("DELETE FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
