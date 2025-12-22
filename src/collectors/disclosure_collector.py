# src/collectors/disclosure_collector.py
import os
import logging
import hashlib
from datetime import datetime, timedelta
import OpenDartReader
from src.db.connection import get_db_cursor
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class DisclosureCollector:
    def __init__(self):
        self.api_key = os.getenv("DART_API_KEY")
        if not self.api_key:
            logger.warning("DART_API_KEY not found in environment variables.")
        self.dart = OpenDartReader(self.api_key) if self.api_key else None

    def _generate_url_hash(self, url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()

    def _fetch_document_content(self, rcept_no: str) -> str:
        """Fetches and simplifies DART document content (Phase 2)"""
        if not self.dart:
            return ""
        try:
            from bs4 import BeautifulSoup
            html = self.dart.document(rcept_no)
            if not html:
                return ""
            
            soup = BeautifulSoup(html, 'html.parser')
            # Extract text from tables which usually contain the core data
            # Also remove scripts and styles
            for script in soup(["script", "style"]):
                script.extract()
                
            text = soup.get_text(separator=' ', strip=True)
            # Limit length to avoid overwhelming the tokenizer, while keeping key info
            return text[:5000]
        except Exception as e:
            logger.error(f"Error fetching document {rcept_no}: {e}")
            return ""

    def collect(self, stock_code: str, start_date: str = None, end_date: str = None):
        """
        Collect disclosures for a specific stock and date range.
        start_date, end_date: 'YYYYMMDD'
        """
        if not self.dart:
            logger.error("OpenDartReader not initialized. Check DART_API_KEY.")
            return

        if not start_date:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y%m%d')

        logger.info(f"Collecting disclosures for {stock_code} from {start_date} to {end_date}")

        try:
            # 1. Fetch disclosure list
            df = self.dart.list(stock_code, bgn_date=start_date, end_date=end_date)
            
            if df is None or df.empty:
                logger.info(f"No disclosures found for {stock_code} in the given range.")
                return

            # 2. Filter interesting disclosures
            keywords = ["공급계약", "증자", "실적전망", "영업실적", "취득결정", "처분결정", "최대주주"]
            
            collected_count = 0
            with get_db_cursor() as cur:
                for _, row in df.iterrows():
                    report_nm = row['report_nm']
                    if any(kw in report_nm for kw in keywords):
                        rcept_no = row['rcept_no']
                        p_date = row['rcept_dt'] # YYYY.MM.DD
                        url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"
                        url_hash = self._generate_url_hash(url)
                        
                        # 3. Fetch detailed document content (Phase 2)
                        detailed_content = self._fetch_document_content(rcept_no)
                        
                        # 4. Save to DB
                        cur.execute("""
                            INSERT INTO tb_news_url (url_hash, url, source, status, published_at_hint, created_at)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (url_hash) DO UPDATE SET status = 'collected'
                        """, (url_hash, url, 'DART', 'collected', p_date))
                        
                        # Title and content with DART_ prefix
                        title = f"DART_{report_nm}"
                        # Combine title with detailed content
                        content = f"DART_{report_nm}. {detailed_content}"
                        
                        cur.execute("""
                            INSERT INTO tb_news_content (url_hash, title, content, published_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (url_hash) DO UPDATE SET
                            title = EXCLUDED.title,
                            content = EXCLUDED.content
                        """, (url_hash, title, content, p_date))
                        
                        # tb_news_mapping
                        cur.execute("""
                            INSERT INTO tb_news_mapping (url_hash, stock_code)
                            VALUES (%s, %s)
                            ON CONFLICT (url_hash, stock_code) DO NOTHING
                        """, (url_hash, stock_code))
                        
                        collected_count += 1
            
            logger.info(f"Successfully collected {collected_count} disclosures for {stock_code}.")
            return collected_count

        except Exception as e:
            logger.error(f"Error collecting disclosures for {stock_code}: {e}")
            return 0

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    # Test with Samsung Electronics
    collector = DisclosureCollector()
    collector.collect("005930", "20241201", "20251231")
