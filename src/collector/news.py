# src/collector/news.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote
import os
import socket
import hashlib
import json
import time
from datetime import datetime, timedelta
from src.db.connection import get_db_cursor
from src.utils.mq import publish_url, publish_job, publish_daily_job
from src.utils.crawler_helper import get_random_headers, random_sleep, parse_naver_date, get_robust_session
from src.analysis.news_filter import RelevanceScorer

class AddressCollector:
    def __init__(self):
        self.session = get_robust_session()
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
                    # New URL: Insert URL and Mapping, then Publish
                    cur.execute(
                        "INSERT INTO tb_news_url (url_hash, url, status, published_at_hint) VALUES (%s, %s, 'pending', %s)",
                        (url_hash, url, date_hint)
                    )
                    if stock_code:
                        cur.execute(
                            "INSERT INTO tb_news_mapping (url_hash, stock_code) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                            (url_hash, stock_code)
                        )
                    publish_url({"url": url, "url_hash": url_hash, "stock_code": stock_code})
                    count += 1
                    COLLECTOR_URLS_TOTAL.inc() # Metric update
                else:
                    # Existing URL
                    # 1. Update hint if provided
                    if date_hint:
                        cur.execute(
                            "UPDATE tb_news_url SET published_at_hint = %s WHERE url_hash = %s AND published_at_hint IS NULL",
                            (date_hint, url_hash)
                        )
                    
                    # 2. Check and Insert Mapping (Deduplication Fix)
                    if stock_code:
                        cur.execute(
                            "SELECT 1 FROM tb_news_mapping WHERE url_hash = %s AND stock_code = %s",
                            (url_hash, stock_code)
                        )
                        if not cur.fetchone():
                            # Mapping missing, likely cross-referenced news (e.g., Samsung news found in Hynix search)
                            cur.execute(
                                "INSERT INTO tb_news_mapping (url_hash, stock_code) VALUES (%s, %s)",
                                (url_hash, stock_code)
                            )
                            print(f"[+] Added cross-reference mapping: {stock_code} -> {url_hash[:8]}...")
                            
                            # Publish to queue for re-scoring (even if content exists)
                            # The BodyCollector will skip crawling if content is present.
                            publish_url({"url": url, "url_hash": url_hash, "stock_code": stock_code})
                            count += 1
        print(f"Published {count} new URLs to MQ.")

    def handle_job(self, ch, method, properties, body):
        data = json.loads(body)
        job_id = data.get("job_id")
        stock_code = data.get("stock_code")
        stock_name = data.get("stock_name")
        days = data.get("days", 30)
        offset = data.get("offset", 0)
        job_type = data.get("job_type", "backfill")
        
        print(f"[*] Processing {job_type.capitalize()} Job {job_id}: {stock_name} ({stock_code}) for {days} days (offset: {offset})")
        
        # Determine worker identity
        worker_id = f"{socket.gethostname()}_{os.getpid()}"
        
        # Update started_at and heartbeat in DB
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE jobs SET status = 'running', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, worker_id = %s, message = %s WHERE job_id = %s",
                (worker_id, f"Job started by {worker_id}", job_id)
            )
        
        from src.utils.metrics import BACKTEST_PROGRESS
        
        try:
            base_end_date = datetime.now()
            end_date = base_end_date - timedelta(days=offset)
            
            # Use explicit direction
            direction = data.get("direction", "backward")
            task_key = data.get("task_key") # 'recent' or 'historical'
            
            print(f"[*] Job {job_id} [{task_key}]: {direction.capitalize()} Mode")
            
            # Initial status update to 'running'
            with get_db_cursor() as cur:
                cur.execute(
                    "UPDATE jobs SET status = 'running', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, worker_id = %s, message = %s WHERE job_id = %s AND status = 'pending'",
                    (worker_id, f"Current Task: {task_key}", job_id)
                )
            
            # Determine start index based on existing progress (Resume Logic)
            start_i = 0
            with get_db_cursor() as cur:
                cur.execute("SELECT params FROM jobs WHERE job_id = %s", (job_id,))
                res = cur.fetchone()
                if res and res['params']:
                    current_params = res['params']
                    if 'tasks' in current_params and task_key and task_key in current_params['tasks']:
                        stored_progress = current_params['tasks'][task_key].get('progress', 0)
                        if stored_progress > 0:
                            # progress = (i + 1) / days * 100
                            # i + 1 = progress / 100 * days
                            # completed_count = int(stored_progress * days / 100)
                            # start_i should be completed_count
                            start_i = int(stored_progress * days / 100)
                            if start_i > 0:
                                print(f"[*] Resuming Job {job_id} [{task_key}] from Step {start_i+1}/{days} (Progress: {stored_progress}%)")

            # Loop through days
            for i in range(days):
                if i < start_i:
                    continue

                # Check for stop request
                with get_db_cursor() as cur:
                    cur.execute("SELECT status, params FROM jobs WHERE job_id = %s", (job_id,))
                    row = cur.fetchone()
                    if not row or row['status'] == 'stop_requested':
                        if row and row['status'] == 'stop_requested':
                            cur.execute("UPDATE jobs SET status = 'stopped', completed_at = CURRENT_TIMESTAMP WHERE job_id = %s", (job_id,))
                        if ch and method: ch.basic_ack(delivery_tag=method.delivery_tag)
                        return
                    
                    params = row['params']
                
                # Check for zombie reset status (if job was reset to pending externally but we are still running?)
                # Actually, if we are running, status should be 'running'.
                # But if we just restarted, we set it to 'running' above.
                
                if direction == 'forward':
                    target_date = (end_date - timedelta(days=days-1)) + timedelta(days=i)
                else:
                    target_date = end_date - timedelta(days=i)

                ds = target_date.strftime("%Y.%m.%d")
                msg = f"[{task_key}] Step {i+1}/{days}: Collecting for {ds}"
                self.collect_by_range(stock_code, ds, ds, query=stock_name, job_id=job_id)
                
                # Keep MQ connection alive during loop (if in same process)
                if ch and ch.connection.is_open:
                    try:
                        ch.connection.process_data_events()
                    except:
                        pass
                
                # Update task-specific progress in JSONB
                task_progress = round(((i + 1) / days) * 100, 2)
                with get_db_cursor() as cur:
                    cur.execute("SELECT params FROM jobs WHERE job_id = %s FOR UPDATE", (job_id,))
                    current_params = cur.fetchone()['params']
                    
                    if 'tasks' in current_params and task_key and task_key in current_params['tasks']:
                        current_params['tasks'][task_key]['progress'] = task_progress
                        all_tasks = current_params['tasks'].values()
                        global_progress = sum(t['progress'] for t in all_tasks) / len(all_tasks)
                        
                        cur.execute(
                            "UPDATE jobs SET progress = %s, params = %s, updated_at = CURRENT_TIMESTAMP, message = %s WHERE job_id = %s",
                            (round(global_progress, 2), json.dumps(current_params), msg, job_id)
                        )
                    else:
                        global_progress = task_progress
                        cur.execute(
                            "UPDATE jobs SET progress = %s, updated_at = CURRENT_TIMESTAMP, message = %s WHERE job_id = %s",
                            (global_progress, msg, job_id)
                        )
                    
                    # Also update Prometheus metric for unified tracking
                    # We prefix Job ID with "J" to distinguish from Verification Job IDs
                    BACKTEST_PROGRESS.labels(job_id=f"J{job_id}", stock_code=stock_code, job_type=job_type).set(global_progress)
                
                time.sleep(1) # Be gentle

            # Finalize Task
            with get_db_cursor() as cur:
                cur.execute("SELECT params FROM jobs WHERE job_id = %s FOR UPDATE", (job_id,))
                current_params = cur.fetchone()['params']
                
                all_done = True
                if 'tasks' in current_params and task_key and task_key in current_params['tasks']:
                    current_params['tasks'][task_key]['status'] = 'completed'
                    current_params['tasks'][task_key]['progress'] = 100
                    all_done = all(t['status'] == 'completed' for t in current_params['tasks'].values())
                    cur.execute("UPDATE jobs SET params = %s WHERE job_id = %s", (json.dumps(current_params), job_id))
                
                if all_done:
                    cur.execute(
                        "UPDATE jobs SET status = 'completed', progress = 100, completed_at = CURRENT_TIMESTAMP, message = 'Job Completed' WHERE job_id = %s",
                        (job_id,)
                    )
                    cur.execute(
                        "UPDATE daily_targets SET backfill_completed_at = CURRENT_TIMESTAMP WHERE stock_code = %s",
                        (stock_code,)
                    )
                    print(f"[v] Job {job_id} Fully Completed")
                    try:
                        BACKTEST_PROGRESS.remove(f"J{job_id}", stock_code, job_type)
                    except:
                        pass

                    if data.get("job_type") == 'daily':
                        try:
                            from src.pipeline.master_orchestrator import MasterOrchestrator
                            MasterOrchestrator.trigger_stage_2_training(stock_code, v_type="DAILY_UPDATE")
                        except Exception as chain_e:
                            print(f"[x] Failed to chain daily update via Orchestrator: {chain_e}")
                else:
                    print(f"[*] Task {task_key} for Job {job_id} done. Waiting for sibling.")

        except Exception as e:
            print(f"[x] Job {job_id} task {task_key} failed: {e}")
            with get_db_cursor() as cur:
                cur.execute("UPDATE jobs SET status = 'failed', message = %s WHERE job_id = %s", (f"Task {task_key} failed: {str(e)[:50]}", job_id))
        
        if ch and method:
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def collect_by_range(self, stock_code, start_date, end_date, query=None, job_id=None):
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
            # Heartbeat update to prevent zombie kill
            # Heartbeat update to prevent zombie kill
            if job_id:
                try:
                    with get_db_cursor() as cur:
                        cur.execute("UPDATE jobs SET updated_at = CURRENT_TIMESTAMP WHERE job_id = %s", (job_id,))
                        # If no rows updated, job is deleted/stopped -> Abort
                        if cur.rowcount == 0:
                            print(f"[!] Job {job_id} not found in DB (Deleted). Aborting worker process.")
                             # Clean up metrics immediately
                            from src.utils.metrics import BACKTEST_PROGRESS
                            try:
                                # Need to infer job_type, default to backfill as this is cleanup
                                BACKTEST_PROGRESS.remove(f"J{job_id}", stock_code, "backfill")
                            except:
                                # Try 'daily' just in case
                                try: BACKTEST_PROGRESS.remove(f"J{job_id}", stock_code, "daily")
                                except: pass
                            return # Exit function
                except Exception:
                    pass

            url = base_search_url.format(
                query=quote(query),
                ds=start_date,
                de=end_date,
                start=start_index
            )
            
            # Manual Retry Loop for Search Page (Extra protection)
            max_retries = 3
            success = False
            for attempt in range(max_retries):
                try:
                    headers = get_random_headers()
                    # Naver sometimes rejects requests with 'br' encoding if not handled properly by client
                    if 'Accept-Encoding' in headers:
                        del headers['Accept-Encoding']
                    
                    response = self.session.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    success = True
                    break
                except Exception as e:
                    is_conn_error = any(msg in str(e).lower() for msg in ["broken pipe", "connection aborted", "connection reset"])
                    if is_conn_error and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5
                        print(f"[!] Connection issue ({e}). Retrying in {wait_time}s... (Attempt {attempt + 2}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    
                    print(f"Error during search collection: {e}")
                    if "403" in str(e) or "429" in str(e):
                        print(f"Hit {e}. Triggering VPN Rotation and cooling down...")
                        # Trigger VPN rotation
                        try:
                            # Use absolute path or consistent relative path
                            with open("/app/src/.trigger_warp_rotation", "w") as f:
                                f.write(str(e))
                        except Exception as ve:
                            print(f"Failed to trigger VPN rotation: {ve}")
                        time.sleep(60) # Wait for rotation and cooldown
                    break # Exit loop on permanent errors or last attempt

            if not success:
                break
            
            # Continue processing if page was successfully fetched
            if "검색결과가 없습니다" in response.text:
                print("No search results found for this query/range.")
                break

            urls = self.extract_urls(response.text, url)
            if not urls:
                # 페이지는 떴는데 URL이 없는 경우
                print("No Naver News URLs found on this page.")
                if any(k in response.text.lower() for k in ["보안", "robot", "captcha"]):
                    print("Blocking detected! Triggering VPN Rotation...")
                    try:
                        with open("/app/src/.trigger_warp_rotation", "w") as f:
                            f.write("block")
                    except Exception as ve:
                        print(f"Failed to trigger VPN rotation: {ve}")
                    time.sleep(60) # Cooldown
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
                

        print(f"Finished collecting for {start_date} - {end_date}. Total pages: {page_count}")

        # --- [Market Data Sync Hook] ---
        # Automatically sync price and fundamentals for the same date range
        try:
            from src.collectors.price_collector import PriceCollector
            from src.collectors.fundamentals_collector import FundamentalsCollector
            
            p_collector = PriceCollector()
            f_collector = FundamentalsCollector()
            
            # pykrx format: YYYYMMDD
            fmt_start = start_date.replace(".", "")
            fmt_end = end_date.replace(".", "")
            
            print(f"[*] Syncing Market Data: {stock_code} ({fmt_start} ~ {fmt_end})")
            
            # 1. Sync Fundamentals
            f_collector.collect(stock_code, fmt_start, fmt_end)
            
            # 2. Sync Prices & Settle Predictions
            from datetime import datetime, timedelta
            curr_dt = datetime.strptime(start_date, "%Y.%m.%d")
            end_dt = datetime.strptime(end_date, "%Y.%m.%d")
            
            while curr_dt <= end_dt:
                ds = curr_dt.strftime("%Y%m%d")
                p_collector.collect_and_settle(stock_code, ds)
                curr_dt += timedelta(days=1)
                
            print(f"[v] Market Data Sync completed for {stock_code}")
        except Exception as sync_e:
            print(f"[!] Market Data Sync failed for {stock_code}: {sync_e}")
        # -------------------------------

class BodyCollector:
    def __init__(self):
        self.session = get_robust_session()
        self.scorer = RelevanceScorer()

    def extract_content(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        # Naver News specific selectors
        title = soup.select_one('h2#title_area') or soup.select_one('h3#articleTitle')
        content = soup.select_one('div#newsct_article') or soup.select_one('div#articleBodyContents')
        
        # Smart datetime extraction using data attributes (not hardcoded selectors)
        from src.utils.crawler_helper import extract_naver_datetime
        published_at = extract_naver_datetime(soup)
        
        return {
            "title": title.get_text(strip=True) if title else "",
            "content": content.get_text(strip=True) if content else "",
            "published_at": published_at  # datetime object or None
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
            with get_db_cursor() as cur:
                # 1. Check if content already exists (Light-weight re-scoring optimization)
                cur.execute(
                    "SELECT title, content, published_at FROM tb_news_content WHERE url_hash = %s",
                    (url_hash,)
                )
                row = cur.fetchone()
                
                if row:
                    # Content exists: Skip Crawling
                    # print(f"[*] Content exists for {url_hash[:8]}. Skipping crawl, just re-scoring.")
                    title = row['title']
                    content = row['content']
                    parsed_date = row['published_at']
                else:
                    # Content missing: Crawl
                    random_sleep(1, 3) # Be gentle
                    response = self.session.get(url, headers=get_random_headers(), timeout=10)
                    response.raise_for_status()
                    content_data = self.extract_content(response.text)
                    
                    title = content_data["title"]
                    content = content_data["content"]
                    parsed_date = content_data["published_at"]
                    
                    # Smart extraction already returns datetime object (or None)
                    # Get hint if available as fallback if parsed_date is None
                    if not parsed_date:
                        cur.execute("SELECT published_at_hint FROM tb_news_url WHERE url_hash = %s", (url_hash,))
                        h_row = cur.fetchone()
                        hint = h_row['published_at_hint'] if h_row else None
                        
                        if hint:
                            if isinstance(hint, str):
                                parsed_date = parse_naver_date(hint)
                            else:
                                # date 객체인 경우 datetime으로 변환 (KST 00:00 -> UTC 전날 15:00)
                                parsed_date = datetime.combine(hint, datetime.min.time()) - timedelta(hours=9)
                    
                    # Update status and save content
                    cur.execute(
                        "UPDATE tb_news_url SET status = 'collected', collected_at = CURRENT_TIMESTAMP WHERE url_hash = %s",
                        (url_hash,)
                    )
                    cur.execute(
                        """INSERT INTO tb_news_content (url_hash, title, content, published_at) 
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT (url_hash) DO UPDATE SET 
                           title = EXCLUDED.title, content = EXCLUDED.content, published_at = EXCLUDED.published_at""",
                        (url_hash, title, content, parsed_date)
                    )

                # 2. Mapping & Relevance Scoring (Common for both new/existing content)
                if stock_code:
                    relevance_score = 0
                    is_relevant = True
                    
                    try:
                        # Try to get stock name from data or scorer cache
                        stock_name = data.get("stock_name")
                        if not stock_name and self.scorer:
                            stock_name = self.scorer.get_stock_name(stock_code)
                        
                        if stock_name and self.scorer:
                            relevance_score, is_relevant = self.scorer.calculate_score(content, title, stock_name, stock_code)
                            # print(f"[*] Scored {stock_code}: {relevance_score} (Relevant: {is_relevant})")
                    except Exception as ex:
                        print(f"[!] Scoring failed: {ex}")

                    cur.execute(
                        """INSERT INTO tb_news_mapping (url_hash, stock_code, relevance_score, is_relevant) 
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT (url_hash, stock_code) DO UPDATE SET 
                           relevance_score = EXCLUDED.relevance_score,
                           is_relevant = EXCLUDED.is_relevant""",
                        (url_hash, stock_code, relevance_score, is_relevant)
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
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

class JobManager:
    def create_backfill_job(self, stock_code, days, offset=0):
        with get_db_cursor() as cur:
            cur.execute("SELECT stock_name FROM tb_stock_master WHERE stock_code = %s", (stock_code,))
            row = cur.fetchone()
            stock_name = row['stock_name'] if row else stock_code

        mid = days // 2
        tasks = {
            "recent": {"direction": "backward", "days": mid if mid > 0 else 1, "offset": offset, "status": "pending", "progress": 0},
            "historical": {"direction": "forward", "days": days - mid, "offset": offset + mid, "status": "pending", "progress": 0} if days > mid else None
        }
        # Clean up None tasks
        tasks = {k: v for k, v in tasks.items() if v}

        params = {
            "stock_code": stock_code,
            "stock_name": stock_name,
            "days": days,
            "offset": offset,
            "job_type": "backfill",
            "tasks": tasks
        }

        # Create ONE job record
        with get_db_cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (job_type, params, status) VALUES ('backfill', %s, 'pending') RETURNING job_id",
                (json.dumps(params),)
            )
            job_id = cur.fetchone()['job_id']
            params["job_id"] = job_id
            
            # Ensure target exists and set started_at
            cur.execute(
                """INSERT INTO daily_targets (stock_code, status, started_at) VALUES (%s, 'paused', CURRENT_TIMESTAMP) 
                   ON CONFLICT (stock_code) DO UPDATE SET 
                      started_at = EXCLUDED.started_at,
                      activation_requested_at = CURRENT_TIMESTAMP""", (stock_code,)
            )

        # Publish TWO tasks pointing to the same job_id
        for key, task in tasks.items():
            publish_data = {
                **params,
                "job_id": job_id,
                "task_key": key,
                "direction": task["direction"],
                "days": task["days"],
                "offset": task["offset"]
            }
            publish_job(publish_data)
        
        print(f"Unified Parallel Backfill: Created Job {job_id} with {len(tasks)} sub-tasks.")
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
            
            publish_daily_job(params)
            # Update started_at in daily_targets
            with get_db_cursor() as cur:
                cur.execute("UPDATE daily_targets SET started_at = CURRENT_TIMESTAMP WHERE stock_code = %s", (stock_code,))
            print(f"Published Daily Job {job_id} for {stock_code}")

    def stop_job(self, job_id):
        from src.utils.metrics import BACKTEST_PROGRESS
        with get_db_cursor() as cur:
            # Clean up metrics
            cur.execute("SELECT params FROM jobs WHERE job_id = %s", (job_id,))
            row = cur.fetchone()
            if row and row['params']:
                stock_code = row['params'].get('stock_code', 'UNKNOWN')
                job_type = row.get('job_type', 'backfill')
                try:
                    BACKTEST_PROGRESS.remove(f"J{job_id}", stock_code, job_type)
                except:
                    # Fallback cleanup
                    try: BACKTEST_PROGRESS.remove(f"J{job_id}", stock_code, "backfill")
                    except: pass
                    try: BACKTEST_PROGRESS.remove(f"J{job_id}", stock_code, "daily")
                    except: pass
                    
            cur.execute(
                "UPDATE jobs SET status = 'stop_requested' WHERE job_id = %s AND status = 'running'",
                (job_id,)
            )
            return cur.rowcount > 0

    def create_gap_backfill_jobs(self, stock_code):
        # 1. Find the date bounds
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT MIN(published_at_hint) as min_date, MAX(published_at_hint) as max_date
                FROM tb_news_mapping nm
                JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
                WHERE nm.stock_code = %s
            """, (stock_code,))
            row = cur.fetchone()
            if not row or not row['min_date']:
                return 0
            
            min_date = row['min_date']
            max_date = row['max_date']
            
            # 2. Find all dates in between that have NO news
            cur.execute("""
                WITH daily_presence AS (
                    SELECT DISTINCT nu.published_at_hint
                    FROM tb_news_mapping nm
                    JOIN tb_news_url nu ON nm.url_hash = nu.url_hash
                    WHERE nm.stock_code = %s
                )
                SELECT gs.d::date as missing_date
                FROM generate_series(%s::date, %s::date, '1 day'::interval) gs(d)
                LEFT JOIN daily_presence dp ON gs.d::date = dp.published_at_hint
                WHERE dp.published_at_hint IS NULL
                ORDER BY gs.d ASC
            """, (stock_code, min_date, max_date))
            missing_dates = [r['missing_date'] for r in cur.fetchall()]
            
            if not missing_dates:
                return 0
            
            # 3. Group missing dates into contiguous ranges
            ranges = []
            if missing_dates:
                from datetime import timedelta
                start = missing_dates[0]
                prev = start
                for d in missing_dates[1:]:
                    if d == prev + timedelta(days=1):
                        prev = d
                    else:
                        ranges.append((start, prev))
                        start = d
                        prev = d
                ranges.append((start, prev))
            
            # 4. Create a backfill job for each range
            today = datetime.now().date()
            job_ids = []
            for r_start, r_end in ranges:
                days = (r_end - r_start).days + 1
                offset = (today - r_end).days
                if offset < 0: offset = 0
                job_id = self.create_backfill_job(stock_code, days, offset=offset)
                job_ids.append(job_id)
                
            return len(job_ids)

if __name__ == "__main__":
    # Example usage
    collector = AddressCollector()
    # This would be triggered by a scheduler or manual job
    # target_url = "..."
    # response = requests.get(target_url)
    # urls = collector.extract_urls(response.text, target_url)
    # collector.process_urls(urls)
    pass
