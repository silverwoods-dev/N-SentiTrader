import os
import json
import re
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

# Global Cache for Aliases
STOCK_ALIAS_MAP = None

def get_stock_aliases(stock_name, stock_code=None):
    """
    Generate aliases using a dynamic alias map (built from all stocks)
    to identify unique keywords and filter common connectors automatically.
    """
    global STOCK_ALIAS_MAP
    
    # 1. Try to load from the pre-built JSON map
    if STOCK_ALIAS_MAP is None:
        alias_json = os.path.join(os.environ.get("NS_DATA_PATH", "data"), "stock_aliases.json")
        if os.path.exists(alias_json):
            try:
                with open(alias_json, 'r', encoding='utf-8') as f:
                    STOCK_ALIAS_MAP = json.load(f)
            except Exception:
                STOCK_ALIAS_MAP = {}
        else:
            STOCK_ALIAS_MAP = {}

    # 2. If code provided and map hit, return it
    if stock_code and stock_code in STOCK_ALIAS_MAP:
        return set(STOCK_ALIAS_MAP[stock_code])

    # 3. Fallback: MeCab + Lite Heuristic (for new stocks not yet synced)
    from src.nlp.tokenizer import Tokenizer
    tokenizer = Tokenizer()
    
    # Simple split & English handling
    base_tokens = tokenizer.tokenize(stock_name, n_gram=1)
    aliases = set(base_tokens)
    aliases.add(stock_name.strip())
    
    # Minimal Suffixes (safety net)
    suffixes = ["전자", "홀딩스", "생명", "화재", "SDI", "디스플레이", "전기", "중공업", "바이오"]
    name_clean = stock_name.strip()
    for sx in suffixes:
        if name_clean.endswith(sx) and len(name_clean) > len(sx):
            aliases.add(name_clean.replace(sx, "").strip())

    final_aliases = set()
    for a in aliases:
        if not a: continue
        final_aliases.add(a)
        if re.search(r'[a-zA-Z]', a):
            eng = "".join(re.findall(r'[a-zA-Z]', a))
            if len(eng) >= 2:
                final_aliases.add(eng.lower())
                final_aliases.add(eng.upper())
                final_aliases.add(eng.capitalize())
            
    return {a for a in final_aliases if len(a) >= 2}

def rem_all_non_eng(text):
    return re.findall(r'[a-zA-Z]+', text)
