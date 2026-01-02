#!/usr/bin/env python3
"""
Stock Master Sync Script
Syncs all KOSPI and KOSDAQ stocks from Naver Finance to tb_stock_master table.
Uses Naver Finance's stock search API for reliable data.

Usage:
    python -m src.scripts.sync_stock_master
"""

import logging
import requests
from src.db.connection import get_db_cursor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def fetch_stocks_from_naver(market: str):
    """Fetch all stocks from a specific market using Naver Finance API
    
    Args:
        market: 'KOSPI' or 'KOSDAQ'
    """
    stocks = []
    page = 1
    per_page = 100
    
    # Naver uses marketType codes: KOSPI=0, KOSDAQ=1
    market_code = '0' if market == 'KOSPI' else '1'
    
    while True:
        try:
            # Naver Finance stock listing API
            url = f"https://m.stock.naver.com/api/stocks/marketValue/{market}?page={page}&pageSize={per_page}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('stocks', [])
            if not items:
                break
                
            for item in items:
                code = item.get('stockCode', '')
                name = item.get('stockName', '')
                if code and name:
                    stocks.append({
                        'code': code,
                        'name': name,
                        'market': market
                    })
            
            # Check if we have more pages
            if len(items) < per_page:
                break
            page += 1
            
            # Safety limit
            if page > 50:
                break
                
        except Exception as e:
            logger.error(f"Error fetching page {page} for {market}: {e}")
            break
    
    return stocks


def fetch_stocks_simple():
    """Simple approach: Use Naver's search autocomplete which has all stocks"""
    stocks = []
    
    # Common stock name patterns to search
    # This won't get ALL stocks but will get most actively searched ones
    # For a complete list we'll fall back to local DB + incremental
    
    # Alternative: Use Naver's markey overview pages to scrape
    markets = [('KOSPI', '0'), ('KOSDAQ', '1')]
    
    for market_name, market_code in markets:
        try:
            # Use mobile API which is simpler
            url = f"https://m.stock.naver.com/api/index/{market_name}/marketSum"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            # Get total stock count for info
            total = data.get('stockCount', 0)
            logger.info(f"{market_name} reported total: {total} stocks")
            
        except Exception as e:
            logger.debug(f"Could not get market summary: {e}")
    
    # Use the full stock list endpoint
    for market_name, market_code in markets:
        page = 1
        while True:
            try:
                url = f"https://m.stock.naver.com/api/stocks/marketValue/{market_name}?page={page}&pageSize=100"
                response = requests.get(url, timeout=10, headers={
                    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)'
                })
                response.raise_for_status()
                data = response.json()
                
                items = data.get('stocks', [])
                if not items:
                    break
                
                for item in items:
                    stocks.append({
                        'code': item.get('itemCode', item.get('reutersCode', '')),
                        'name': item.get('stockName', ''),
                        'market': market_name
                    })

                
                if len(items) < 100:
                    break
                page += 1
                
                if page > 30:  # Safety limit
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching {market_name} page {page}: {e}")
                break
        
        logger.info(f"Fetched {len([s for s in stocks if s['market'] == market_name])} {market_name} stocks")
    
    return stocks


def sync_all_stocks():
    """Sync all stocks to tb_stock_master"""
    
    logger.info("Starting stock master sync...")
    
    all_stocks = fetch_stocks_simple()
    
    if not all_stocks:
        logger.error("No stocks fetched. Aborting sync.")
        return 0
    
    logger.info(f"Total stocks to sync: {len(all_stocks)}")
    
    # Upsert to database
    upserted = 0
    
    with get_db_cursor() as cur:
        for s in all_stocks:
            if not s['code']:
                continue
            try:
                cur.execute("""
                    INSERT INTO tb_stock_master (stock_code, stock_name, market_type)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (stock_code) DO UPDATE SET
                        stock_name = EXCLUDED.stock_name,
                        market_type = EXCLUDED.market_type
                """, (s['code'], s['name'], s['market']))
                upserted += 1
            except Exception as e:
                logger.error(f"Error upserting {s['code']}: {e}")

    
    logger.info(f"Sync completed: {upserted} stocks upserted")
    return upserted


def count_stocks():
    """Print current stock count by market"""
    with get_db_cursor() as cur:
        cur.execute("""
            SELECT market_type, COUNT(*) as cnt 
            FROM tb_stock_master 
            GROUP BY market_type
            ORDER BY market_type
        """)
        rows = cur.fetchall()
        
        total = 0
        for row in rows:
            market = row['market_type'] or 'Unknown'
            count = row['cnt']
            total += count
            print(f"  {market}: {count}")
        print(f"  Total: {total}")


if __name__ == "__main__":
    print("=" * 50)
    print("Stock Master Sync (Naver Finance)")
    print("=" * 50)
    
    print("\n[Before Sync]")
    count_stocks()
    
    print("\n[Syncing...]")
    sync_all_stocks()
    
    print("\n[After Sync]")
    count_stocks()
    
    print("\nDone!")
