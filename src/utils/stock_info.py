
import requests
from bs4 import BeautifulSoup
from src.utils.crawler_helper import get_random_headers

def get_stock_name(stock_code):
    """
    Fetch stock name from Naver Finance given a stock code.
    Returns the stock name if found, otherwise returns manual fallback or None.
    """
    url = f"https://finance.naver.com/item/main.naver?code={stock_code}"
    
    try:
        response = requests.get(url, headers=get_random_headers(), timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Naver Finance stock name selector
        # Usually it's in <div class="wrap_company"><h2><a href="#">Stock Name</a></h2></div>
        # Or sometimes just <h2><a ...>Stock Name</a></h2> inside wrap_company
        
        # Selector approach
        # The structure is: div.wrap_company > h2 > a
        name_el = soup.select_one(".wrap_company h2 a")
        if name_el:
            return name_el.get_text(strip=True)
            
        # Fallback check if it's a valid page but selector changed?
        # Maybe check title? Title usually is "Company Name : Naver Finance"
        title = soup.title.string if soup.title else ""
        if ":" in title:
            # "삼성전자 : 네이버페이 증권"
            potential_name = title.split(":")[0].strip()
            if potential_name:
                return potential_name
                
    except Exception as e:
        print(f"Error fetching stock name for {stock_code}: {e}")
    
    return stock_code # Return code as fallback name
