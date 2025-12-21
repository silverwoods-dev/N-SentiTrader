# src/collector/news.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import hashlib
import json
import time
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.utils.mq import publish_url, publish_job
from src.utils.crawler_helper import get_random_headers, random_sleep, parse_naver_date

class AddressCollector:
    def __init__(self):
        self.session = requests.Session()
        # 초기 쿠키 설정을 위해 메인 페이지 방문
        try:
            self.session.get("https://www.naver.com", headers=get_random_headers(), timeout=10)
        except:
            pass

    def extract_urls(self, html, base_url):
        soup = BeautifulSoup(html, 'html.parser')
        urls = []
        # Naver News search result specific selectors
        # New layout uses obfuscated classes, so we look for all links pointing to Naver News
        for a in soup.select('a'):
            href = a.get('href', '')
            if 'n.news.naver.com' in href or 'news.naver.com' in href:
                # Clean up URL
                if '?' in href:
                    base = href.split('?')[0]
                    params = href.split('?')[1].split('&')
                    # Keep only essential params to avoid duplicates
                    essential = [p for p in params if p.startswith('articleId') or p.startswith('oid') or p.startswith('article') or p.startswith('sid')]
                    if essential:
                        href = base + '?' + '&'.join(essential)
                urls.append(href)
        
        unique_urls = list(set(urls))
        print(f"Found {len(unique_urls)} Naver News URLs on this page.")
        return unique_urls

    def get_url_hash(self, url):
        # URL에서 불필요한 파라미터 제거하여 해시 일관성 유지
        clean_url = url.split('?')[0]
        if '?' in url:
            params = url.split('?')[1].split('&')
            # articleId, oid 또는 article/sid 등 핵심 정보만 추출
            key_params = sorted([p for p in params if any(k in p for k in ['article', 'oid', 'sid'])])
            if key_params:
                clean_url += '?' + '&'.join(key_params)
        
        return hashlib.sha256(clean_url.encode()).hexdigest()

    def process_urls(self, urls, stock_code=None, date_hint=None):
        from src.utils.metrics import COLLECTOR_URLS_TOTAL
        
        count = 0
        for url in urls:
            url_hash = self.get_url_hash(url)
            with get_db_cursor() as cur:
                cur.execute("SELECT 1 FROM tb_news_url WHERE url_hash = %s", (url_hash,))
                if not cur.fetchone():
                    # New URL
                    cur.execute(
                        "INSERT INTO tb_news_url (url_hash, url, status, published_at_hint) VALUES (%s, %s, 'pending', %s)",
                        (url_hash, url, date_hint)
                    )
                    publish_url({"url": url, "url_hash": url_hash, "stock_code": stock_code})
                    count += 1
                    COLLECTOR_URLS_TOTAL.inc() # Metric update
                else:
                    # Existing URL - update hint if provided
                    if date_hint:
                        cur.execute(
                            "UPDATE tb_news_url SET published_at_hint = %s WHERE url_hash = %s AND published_at_hint IS NULL",
                            (date_hint, url_hash)
                        )
        print(f"Published {count} new URLs to MQ.")

    def handle_job(self, ch, method, properties, body):
        data = json.loads(body)
        job_id = data.get("job_id")
        stock_code = data.get("stock_code")
        stock_name = data.get("stock_name")
        days = data.get("days", 30)
        offset = data.get("offset", 0)
        
        print(f"[*] Processing Job {job_id}: {stock_name} ({stock_code}) for {days} days (offset: {offset})")
        
        # Update started_at in DB
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE jobs SET status = 'running', started_at = CURRENT_TIMESTAMP WHERE job_id = %s",
                (job_id,)
            )
        
        try:
            base_end_date = datetime.now()
            end_date = base_end_date - timedelta(days=offset)
            
            # 수집 이력 확인 (최초 수집인지 증분 수집인지 판별)
            is_incremental = False
            with get_db_cursor() as cur:
                cur.execute("SELECT 1 FROM daily_targets WHERE stock_code = %s AND backfill_completed_at IS NOT NULL", (stock_code,))
                if cur.fetchone():
                    is_incremental = True
            
            print(f"[*] Collection Mode: {'Forward (Oldest -> Newest)' if is_incremental else 'Backward (Newest -> Oldest)'}")
            
            # 일자별로 루프를 돌며 수집
            for i in range(days):
                # 중지 요청 확인
                with get_db_cursor() as cur:
                    cur.execute("SELECT status FROM jobs WHERE job_id = %s", (job_id,))
                    row = cur.fetchone()
                    if not row:
                        print(f"[!] Job {job_id} not found in DB (deleted?). Terminating...")
                        if ch:
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    if row['status'] == 'stop_requested':
                        print(f"[!] Job {job_id} stop requested. Terminating...")
                        cur.execute(
                            "UPDATE jobs SET status = 'stopped', completed_at = CURRENT_TIMESTAMP WHERE job_id = %s",
                            (job_id,)
                        )
                        if ch:
                            ch.basic_ack(delivery_tag=method.delivery_tag)
                        return

                # 수집 방향에 따른 날짜 계산
                if is_incremental:
                    # Forward: 가장 과거부터 시작하여 최신으로 (End - (Days-1) + i)
                    target_date = (end_date - timedelta(days=days-1)) + timedelta(days=i)
                else:
                    # Backward: 최신부터 시작하여 과거로 (End - i)
                    target_date = end_date - timedelta(days=i)

                ds = target_date.strftime("%Y.%m.%d")
                print(f"[*] Step {i+1}/{days}: Collecting for date {ds}")
                self.collect_by_range(stock_code, ds, ds, query=stock_name)
                
                # 진행률 업데이트
                progress = round(((i + 1) / days) * 100, 2) if days > 0 else 100.0
                with get_db_cursor() as cur:
                    cur.execute(
                        "UPDATE jobs SET progress = %s WHERE job_id = %s",
                        (progress, job_id)
                    )
                
                time.sleep(1) # Be gentle to Naver
            
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET status = 'completed', progress = 100, completed_at = CURRENT_TIMESTAMP WHERE job_id = %s",
                    (job_id,)
                )
                # If it was a backfill job, update daily_targets
                if data.get("job_type") == "backfill":
                    # auto_activate_daily가 true면 status를 active로 변경
                    # pending 상태였으면 backfill 완료 후 paused로 전환 (관리자 승인 대기)
                    cur.execute(
                        """UPDATE daily_targets 
                           SET backfill_completed_at = CURRENT_TIMESTAMP,
                               started_at = CASE WHEN auto_activate_daily = true THEN CURRENT_TIMESTAMP ELSE started_at END,
                               status = CASE 
                                   WHEN auto_activate_daily = true THEN 'active' 
                                   WHEN status = 'pending' THEN 'paused'
                                   ELSE status 
                               END
                           WHERE stock_code = %s""",
                        (stock_code,)
                    )
            print(f"[v] Job {job_id} completed.")
            
        except Exception as e:
            print(f"[x] Job {job_id} failed: {e}")
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET status = 'failed' WHERE job_id = %s",
                    (job_id,)
                )
        
        if ch:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def collect_by_range(self, stock_code, start_date, end_date, query=None):
        """
        Collect news URLs for a stock code within a date range.
        start_date, end_date: YYYY.MM.DD format
        """
        if not query:
            query = stock_code
            
        base_search_url = "https://search.naver.com/search.naver?where=news&query={query}&sm=tab_pge&sort=0&photo=0&field=0&pd=3&ds={ds}&de={de}&start={start}"
        
        # Use start_date as hint if it's a single day range
        date_hint = None
        if start_date == end_date:
            try:
                date_hint = datetime.strptime(start_date, "%Y.%m.%d").date()
            except:
                pass
        
        start_index = 1
        page_count = 0
        max_pages = 10 # Safety limit
        
        while page_count < max_pages:
            url = base_search_url.format(
                query=quote(query),
                ds=start_date,
                de=end_date,
                start=start_index
            )
            
            print(f"Fetching page {page_count + 1} (start={start_index}): {url}")
            try:
                headers = get_random_headers()
                if 'Accept-Encoding' in headers:
                    del headers['Accept-Encoding']
                
                response = self.session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                if "검색결과가 없습니다" in response.text:
                    print("No search results found for this query/range.")
                    break

                urls = self.extract_urls(response.text, url)
                if not urls:
                    # 페이지는 떴는데 URL이 없는 경우
                    print("No Naver News URLs found on this page.")
                    if "보안" in response.text or "robot" in response.text or "captcha" in response.text.lower():
                        print("Possible blocking detected!")
                    break
                    
                self.process_urls(urls, stock_code, date_hint=date_hint)
                
                # Check if there's a next page (optional, but good for stopping early)
                if "btn_next" not in response.text and "다음" not in response.text:
                    # This is a bit loose, but better than nothing
                    pass

                start_index += 10
                page_count += 1
                random_sleep(2, 5)
                
                if start_index > 1000: 
                    break
                    
            except Exception as e:
                print(f"Error during search collection: {e}")
                if "403" in str(e):
                    print("Hit 403 Forbidden. Triggering VPN Rotation and cooling down...")
                    # Trigger VPN rotation
                    try:
                        with open("/app/src/.trigger_warp_rotation", "w") as f:
                            f.write("403")
                    except Exception as ve:
                        print(f"Failed to trigger VPN rotation: {ve}")
                        
                    time.sleep(60) # Wait for rotation and cooldown
                break

        print(f"Finished collecting for {start_date} - {end_date}. Total pages: {page_count}")

class BodyCollector:
    def __init__(self):
        self.session = requests.Session()

    def extract_content(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Naver News specific selectors
        title = soup.select_one('h2#title_area') or soup.select_one('h3#articleTitle')
        content = soup.select_one('div#newsct_article') or soup.select_one('div#articleBodyContents')
        
        # 날짜 추출 (여러 패턴 대응)
        date_el = (
            soup.select_one('span.media_end_head_info_datestamp_time') or 
            soup.select_one('span._ARTICLE_DATE_TIME') or
            soup.select_one('span.media_end_head_info_dateline_time') or 
            soup.select_one('span.t11')
        )
        
        published_at = None
        if date_el:
            # data-date-time 또는 data-modify-time 속성 우선 확인
            published_at = (
                date_el.get('data-date-time') or 
                date_el.get('data-modify-time') or 
                date_el.get_text(strip=True)
            )
        
        return {
            "title": title.get_text(strip=True) if title else "",
            "content": content.get_text(strip=True) if content else "",
            "published_at": published_at
        }

    def handle_message(self, ch, method, properties, body):
        from src.utils.metrics import COLLECTOR_CONTENT_TOTAL, COLLECTOR_ERRORS_TOTAL

        if isinstance(body, bytes):
            data = json.loads(body)
        else:
            data = body
            
        url = data["url"]
        url_hash = data["url_hash"]
        stock_code = data.get("stock_code")
        
        try:
            random_sleep(1, 3) # Be gentle
            response = self.session.get(url, headers=get_random_headers(), timeout=10)
            response.raise_for_status()
            content_data = self.extract_content(response.text)
            
            # 날짜 파싱 시도
            parsed_date = parse_naver_date(content_data["published_at"])
            
            with get_db_cursor() as cur:
                # Get hint if available
                cur.execute("SELECT published_at_hint FROM tb_news_url WHERE url_hash = %s", (url_hash,))
                row = cur.fetchone()
                hint = row['published_at_hint'] if row else None
                
                # 파싱 결과가 없으면 힌트(날짜)라도 사용
                if not parsed_date and hint:
                    if isinstance(hint, str):
                        parsed_date = parse_naver_date(hint)
                    else:
                        # date 객체인 경우 datetime으로 변환 (KST 00:00 -> UTC 전날 15:00)
                        parsed_date = datetime.combine(hint, datetime.min.time()) - timedelta(hours=9)
                
                # Update status
                cur.execute(
                    "UPDATE tb_news_url SET status = 'collected', collected_at = CURRENT_TIMESTAMP WHERE url_hash = %s",
                    (url_hash,)
                )
                # Insert content
                cur.execute(
                    """INSERT INTO tb_news_content (url_hash, title, content, published_at) 
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (url_hash) DO UPDATE SET 
                       title = EXCLUDED.title, content = EXCLUDED.content, published_at = EXCLUDED.published_at""",
                    (url_hash, content_data["title"], content_data["content"], parsed_date)
                )
                # Mapping
                if stock_code:
                    cur.execute(
                        """INSERT INTO tb_news_mapping (url_hash, stock_code) 
                           VALUES (%s, %s) ON CONFLICT DO NOTHING""",
                        (url_hash, stock_code)
                    )
            
            COLLECTOR_CONTENT_TOTAL.inc() # Metric update
            print(f"Collected: {url}")
            if ch:
                ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            COLLECTOR_ERRORS_TOTAL.labels(type='body_collection').inc() # Metric update
            print(f"Failed to collect {url}: {e}")
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE tb_news_url SET status = 'failed' WHERE url_hash = %s",
                    (url_hash,)
                )
                cur.execute(
                    "INSERT INTO tb_news_errors (url_hash, error_msg) VALUES (%s, %s)",
                    (url_hash, str(e))
                )
            if ch:
                ch.basic_ack(delivery_tag=method.delivery_tag)

class JobManager:
    def create_backfill_job(self, stock_code, days, offset=0):
        params = {"stock_code": stock_code, "days": days, "offset": offset, "job_type": "backfill"}
        with get_db_cursor() as cur:
            # Get stock name
            cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
            row = cur.fetchone()
            stock_name = row['stock_name'] if row else stock_code
            params["stock_name"] = stock_name

            # Create job
            cur.execute(
                "INSERT INTO jobs (job_type, params, status) VALUES ('backfill', %s, 'pending') RETURNING job_id",
                (json.dumps(params),)
            )
            job_id = cur.fetchone()['job_id']
            params["job_id"] = job_id
            
            # Register in daily_targets as paused
            cur.execute(
                """INSERT INTO daily_targets (stock_code, status) 
                   VALUES (%s, 'paused') 
                   ON CONFLICT (stock_code) DO NOTHING""",
                (stock_code,)
            )
            
        # Publish to MQ for parallel processing
        publish_job(params)
        print(f"Created and Published Backfill Job {job_id} for {stock_code} ({stock_name})")
        return job_id

    def get_active_daily_targets(self):
        with get_db_cursor() as cur:
            cur.execute("SELECT stock_code FROM daily_targets WHERE status = 'active'")
            return [row['stock_code'] for row in cur.fetchall()]

    def start_daily_jobs(self):
        targets = self.get_active_daily_targets()
        if not targets:
            print("No active daily targets found.")
            return
        
        for stock_code in targets:
            # Daily job is usually for 1 day (yesterday to today)
            params = {"stock_code": stock_code, "days": 1}
            with get_db_cursor() as cur:
                cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
                row = cur.fetchone()
                stock_name = row['stock_name'] if row else stock_code
                params["stock_name"] = stock_name

                cur.execute(
                    "INSERT INTO jobs (job_type, params, status) VALUES ('daily', %s, 'running') RETURNING job_id",
                    (json.dumps(params),)
                )
                job_id = cur.fetchone()['job_id']
                params["job_id"] = job_id
            
            publish_job(params)
            print(f"Published Daily Job {job_id} for {stock_code}")

    def stop_job(self, job_id):
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE jobs SET status = 'stop_requested' WHERE job_id = %s AND status = 'running'",
                (job_id,)
            )
            return cur.rowcount > 0

if __name__ == "__main__":
    # Example usage
    collector = AddressCollector()
    # This would be triggered by a scheduler or manual job
    # target_url = "..."
    # response = requests.get(target_url)
    # urls = collector.extract_urls(response.text, target_url)
    # collector.process_urls(urls)
    pass
