# src/utils/crawler_helper.py
import random
import time

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

def parse_naver_date(date_str):
    """
    네이버 뉴스 날짜 형식 파싱
    예: 2025.12.18. 오전 11:47 -> datetime 객체
    """
    if not date_str:
        return None
    
    try:
        # 불필요한 문자 제거 및 공백 정리
        clean_str = date_str.replace("입력", "").replace("수정", "").strip()
        
        # 오전/오후 처리
        is_pm = "오후" in clean_str
        clean_str = clean_str.replace("오전", "").replace("오후", "").strip()
        
        # YYYY.MM.DD. HH:MM 형식으로 가정
        # . 이 여러개 있을 수 있으므로 정리
        parts = [p.strip() for p in clean_str.split('.') if p.strip()]
        if len(parts) >= 3:
            date_part = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
            time_part = parts[3] if len(parts) > 3 else "00:00"
            
            # 시간 파싱 (HH:MM)
            h, m = map(int, time_part.split(':'))
            if is_pm and h < 12:
                h += 12
            elif not is_pm and h == 12:
                h = 0
                
            from datetime import datetime, timedelta
            # 네이버 시간은 KST(UTC+9)이므로, 저장 시 UTC로 변환 (9시간 차감)
            kst_dt = datetime.strptime(f"{date_part} {h:02d}:{m:02d}", "%Y-%m-%d %H:%M")
            utc_dt = kst_dt - timedelta(hours=9)
            return utc_dt
    except Exception as e:
        print(f"Date parsing error ({date_str}): {e}")
    
    return None
