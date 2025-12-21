import requests
from src.utils.crawler_helper import get_random_headers
from bs4 import BeautifulSoup

def debug_naver():
    url = "https://search.naver.com/search.naver?where=news&query=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90&sm=tab_opt&sort=0&photo=0&field=0&pd=3&ds=2025.12.17&de=2025.12.17"
    headers = get_random_headers()
    # Remove Accept-Encoding to avoid compression issues if libraries are missing
    if 'Accept-Encoding' in headers:
        del headers['Accept-Encoding']
    
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Encoding: {response.encoding}")
    print(f"Apparent Encoding: {response.apparent_encoding}")
    
    content = response.text
    print(f"Response length: {len(content)}")
    
    # Search for keywords in the raw HTML
    print(f"Contains 'list_news': {'list_news' in content}")
    
    # Print a chunk where 'list_news' might be
    idx = content.find('list_news')
    if idx != -1:
        print(f"Snippet around 'list_news': {content[idx-50:idx+500]}")
    else:
        print("Keyword 'list_news' not found in content")

    soup = BeautifulSoup(content, 'html.parser')
    
    # Find the news list container
    news_list = soup.select_one('ul.list_news')
    # Check for next page button
    next_btn = soup.select_one('a.btn_next')
    if next_btn:
        print(f"Found next button: {next_btn.get('href', 'No href')}")
        print(f"Aria-disabled: {next_btn.get('aria-disabled')}")
        print(f"Classes: {next_btn.get('class', [])}")
    else:
        print("Next button (a.btn_next) not found")
        # Try alternative
        next_btn = soup.select_one('a[aria-label="다음"]')
        if next_btn:
            print("Found next button via aria-label")
        else:
            # Search for any link with '다음' text
            for a in soup.select('a'):
                if '다음' in a.text:
                    print(f"Found potential next link with text '다음': {a.get('href')}")
                    break
        print("ul.list_news not found")

if __name__ == "__main__":
    debug_naver()
