
import os
import sys
import json
from bs4 import BeautifulSoup

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

from src.collector.news import AddressCollector, BodyCollector

def test_phase44():
    print("[-] Starting Phase 44 Verification...")
    
    # 1. Find a URL
    ac = AddressCollector()
    target_page = "https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=101" # Economy
    print(f"[-] Fetching URL list from {target_page}...")
    
    # Use a real Desktop User-Agent
    UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    try:
        resp = ac.session.get(target_page, headers={'User-Agent': UA})
        urls = ac.extract_urls(resp.text, target_page)
        
        if not urls:
            print("[!] No URLs found. Aborting.")
            return
            
        test_url = urls[0] # Pick first one
        print(f"[-] Selected Test URL: {test_url}")
        
    except Exception as e:
        print(f"[!] Failed to fetch URLs: {e}")
        return

    # 2. Extract Content (New Logic)
    bc = BodyCollector()
    print("[-] Extracting content with JSON-LD logic...")
    
    try:
        resp = bc.session.get(test_url, headers={'User-Agent': UA})
        data = bc.extract_content(resp.text)
        
        print("\n" + "="*50)
        print("VERIFICATION RESULTS")
        print("="*50)
        print(f"Title       : {data['title']}")
        print(f"Date        : {data['published_at']}")
        print(f"Is JSON-LD  : {data['is_json_ld']}")
        print(f"Author      : {data['author_name']}")
        print(f"Source      : {data['source_name']}")
        print(f"Image URL   : {data['image_url']}")
        print(f"Meta Size   : {len(json.dumps(data['meta_data'])) if data['meta_data'] else 0} bytes")
        print("="*50 + "\n")
        
        if data['is_json_ld'] and data['author_name']:
            print("[v] SUCCESS: JSON-LD detected and Author Name extracted.")
        elif data['is_json_ld']:
             print("[v] SUCCESS: JSON-LD detected (Author might be missing in source).")
        else:
            print("[x] FAILURE: Fallback to old logic (No JSON-LD found).")
            
            # Debug: Check HTML content
            print("\n[-] DEBUG INFO:")
            if "application/ld+json" in resp.text:
                print("    Found 'application/ld+json' string in HTML! Parsing logic might be wrong.")
                soup = BeautifulSoup(resp.text, 'html.parser')
                scripts = soup.find_all('script', type='application/ld+json')
                print(f"    Found {len(scripts)} ld+json script tags.")
                for i, s in enumerate(scripts):
                    print(f"    Script {i} Content (first 100 chars): {s.string[:100] if s.string else 'None'}")
            else:
                print("    'application/ld+json' NOT found in HTML. Naver might have changed format.")
                print(f"    Page Snippet: {resp.text[:500]}...")

    except Exception as e:
        print(f"[!] Extraction failed: {e}")

if __name__ == "__main__":
    test_phase44()
