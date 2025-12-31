# src/utils/crawler_helper.py
import random
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def get_robust_session(retries=3, backoff_factor=1, status_forcelist=(500, 502, 503, 504)):
    """
    Returns a requests.Session with an HTTPAdapter configured for retries.
    This handles BrokenPipeError, ConnectionError, and transient 5xx errors.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# 고정된 최신 브라우저 User-Agent 리스트
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.naver.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }

def random_sleep(min_sec=3, max_sec=6):
    time.sleep(random.uniform(min_sec, max_sec))

def extract_naver_datetime(soup):
    """
    Smart datetime extraction from Naver news HTML.
    Uses attribute-based search instead of hardcoded selectors.
    
    Returns:
        str: Datetime string if found, None otherwise
    """
    from datetime import datetime, timedelta
    
    # Strategy 1: Look for data-date-time attribute (most reliable)
    # This works regardless of class names or HTML structure changes
    for elem in soup.find_all(attrs={'data-date-time': True}):
        date_str = elem.get('data-date-time')
        if date_str:
            try:
                # Format: "2025-12-26 04:42:15" (KST)
                kst_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                utc_dt = kst_dt - timedelta(hours=9)
                return utc_dt
            except:
                pass
    
    # Strategy 2: Look for data-modify-date-time as fallback
    for elem in soup.find_all(attrs={'data-modify-date-time': True}):
        date_str = elem.get('data-modify-date-time')
        if date_str:
            try:
                kst_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                utc_dt = kst_dt - timedelta(hours=9)
                return utc_dt
            except:
                pass
    
    # Strategy 3: Look for any element with datetime-related data attributes
    for elem in soup.find_all():
        for attr_name in elem.attrs:
            if 'date' in attr_name.lower() and 'time' in attr_name.lower():
                date_str = elem.get(attr_name)
                if date_str and isinstance(date_str, str):
                    # Try multiple formats
                    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                        try:
                            kst_dt = datetime.strptime(date_str, fmt)
                            utc_dt = kst_dt - timedelta(hours=9)
                            return utc_dt
                        except:
                            continue
    
    return None


def extract_json_ld(soup):
    """
    Extract structured data (JSON-LD) from Naver news HTML.
    Returns a dictionary with NewsArticle properties if found.
    """
    import json
    
    # Find all JSON-LD scripts
    scripts = soup.find_all('script', type='application/ld+json')
    
    for script in scripts:
        try:
            data = json.loads(script.string)
            
            # Handle list of objects
            if isinstance(data, list):
                items = data
            else:
                items = [data]
            
            for item in items:
                # Look for NewsArticle or ReportageNewsArticle
                if item.get('@type') in ['NewsArticle', 'ReportageNewsArticle', 'Article']:
                    
                    # Extract Author
                    author_data = item.get('author')
                    author_name = None
                    if isinstance(author_data, dict):
                        author_name = author_data.get('name')
                    elif isinstance(author_data, list) and len(author_data) > 0:
                         author_name = author_data[0].get('name')
                    elif isinstance(author_data, str):
                        author_name = author_data

                    # Extract Publisher (Source)
                    publisher_data = item.get('publisher')
                    source_name = None
                    if isinstance(publisher_data, dict):
                        source_name = publisher_data.get('name')
                    
                    # Extract Image
                    image_data = item.get('image')
                    image_url = None
                    if isinstance(image_data, dict):
                         image_url = image_data.get('url')
                    elif isinstance(image_data, str):
                        image_url = image_data

                    # Extract Date
                    date_published = item.get('datePublished')
                    
                    return {
                        "is_json_ld": True,
                        "title": item.get('headline'),
                        "description": item.get('description'),
                        "published_at": date_published, # String format, needs parsing
                        "author_name": author_name,
                        "source_name": source_name,
                        "image_url": image_url,
                        "raw_data": item # Store full object for meta_data column
                    }
        except Exception as e:
            print(f"JSON-LD parsing error: {e}")
            continue
    
    # Fallback to OpenGraph
    og_data = {}
    for meta in soup.find_all('meta', property=True):
        prop = meta.get('property')
        if prop and prop.startswith('og:'):
            og_data[prop] = meta.get('content')
            
    # Also look for article:author specifically
    author_meta = soup.find('meta', property='article:author') or soup.find('meta', attrs={'name': 'author'})
    author_name = author_meta.get('content') if author_meta else None
    
    # Naver specific: twitter:creator often holds the journalist name
    if not author_name:
        creator_meta = soup.find('meta', attrs={'name': 'twitter:creator'}) or soup.find('meta', property='twitter:creator')
        author_name = creator_meta.get('content') if creator_meta else None

    # Naver specific: trying to parse "OOO 기자" from byline if not in meta
    if not author_name:
        byline = soup.select_one('.byline_s') or soup.select_one('.media_end_head_journalist_name')
        if byline:
            author_name = byline.get_text(strip=True).split(' ')[0] # "홍길동 기자" -> "홍길동"

    if og_data:
        # Check if we have enough "rich" data to consider it structured success
        # We need at least title and (image OR author OR source)
        return {
            "is_json_ld": False, # It's structured, but not JSON-LD
            "title": og_data.get('og:title'),
            "description": og_data.get('og:description'),
            "published_at": None, # OG usually doesn't have precise publish time, let fallback handle it
            "author_name": author_name,
            "source_name": og_data.get('og:site_name') or "Naver News",
            "image_url": og_data.get('og:image'),
            "raw_data": og_data # Store OG data
        }
            
    return None

def parse_naver_date(date_str):
    """
    네이버 뉴스 날짜 형식 파싱 (Legacy 텍스트 기반)
    새로운 코드는 extract_naver_datetime()을 우선 사용해야 함
    
    예: 
    - 2025.12.18. 오전 11:47
    - 2025-12-24T09:10:00+09:00
    - 입력 2025.12.24. 오전 9:10
    """
    if not date_str:
        return None
    
    from datetime import datetime, timedelta
    import re
    
    try:
        # Case 1: Already in standard format (from data attributes)
        if isinstance(date_str, datetime):
            return date_str
            
        # Case 2: ISO-like format
        if 'T' in date_str:
            date_str = date_str.replace('+09:00', '').replace('Z', '')
            kst_dt = datetime.fromisoformat(date_str)
            utc_dt = kst_dt - timedelta(hours=9)
            return utc_dt
      
        # Case 3: YYYY-MM-DD HH:MM:SS format (from data attributes)
        if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', date_str):
            kst_dt = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            utc_dt = kst_dt - timedelta(hours=9)
            return utc_dt
        
        # Case 4: Korean format with 오전/오후
        clean_str = date_str.replace("입력", "").replace("수정", "").strip()
        is_pm = "오후" in clean_str
        clean_str = clean_str.replace("오전", "").replace("오후", "").strip()
        
        parts = [p.strip() for p in clean_str.split('.') if p.strip()]
        if len(parts) >= 3:
            date_part = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            time_part = parts[3] if len(parts) > 3 else "00:00"
            
            time_match = re.search(r'(\d{1,2}):(\d{2})', time_part)
            if time_match:
                h, m = int(time_match.group(1)), int(time_match.group(2))
            else:
                h, m = 0, 0
                
            if is_pm and h < 12:
                h += 12
            elif not is_pm and h == 12:
                h = 0
                
            kst_dt = datetime.strptime(f"{date_part} {h:02d}:{m:02d}", "%Y-%m-%d %H:%M")
            utc_dt = kst_dt - timedelta(hours=9)
            return utc_dt
    except Exception as e:
        print(f"Date parsing error ({date_str}): {e}")
    
    return None
