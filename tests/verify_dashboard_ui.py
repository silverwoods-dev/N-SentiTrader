import asyncio
from playwright.async_api import async_playwright
import os

async def verify_dashboard():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 대시보드 접속 (컨테이너 내부 또는 로컬 호스트 환경 고려)
        url = os.getenv("DASHBOARD_URL", "http://localhost:8080")
        print(f"Connecting to {url}...")
        
        try:
            await page.goto(url, timeout=10000)
            print("Page loaded successfully.")
            
            # 1. Bento Grid 레이아웃 확인 (Tailwind 클래스 grid-cols-12 등)
            grid = await page.query_selector(".grid-cols-12")
            if grid:
                print("✅ Bento Grid layout detected.")
            else:
                print("❌ Bento Grid layout NOT detected.")
            
            # 2. HTMX 폴링 요소 확인 (hx-get, hx-trigger)
            jobs_list = await page.query_selector("#jobs-list")
            if jobs_list:
                hx_get = await jobs_list.get_attribute("hx-get")
                hx_trigger = await jobs_list.get_attribute("hx-trigger")
                print(f"✅ HTMX Jobs List detected. hx-get: {hx_get}, hx-trigger: {hx_trigger}")
            
            # 3. Chart.js 캔버스 확인
            chart = await page.query_selector("#newsChart")
            if chart:
                print("✅ News Distribution Chart (Chart.js) detected.")
            
            # 4. Toast 컨테이너 확인
            toast_container = await page.query_selector("#toast-container")
            if toast_container:
                print("✅ Toast notification container detected.")
            
            # 5. Lucide 아이콘 확인
            icons = await page.query_selector_all("i[data-lucide]")
            print(f"✅ {len(icons)} Lucide icons detected.")
            
            # 스크린샷 저장
            await page.screenshot(path="tests/output/dashboard_verification.png", full_page=True)
            print("✅ Screenshot saved to tests/output/dashboard_verification.png")
            
        except Exception as e:
            print(f"❌ Error during verification: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_dashboard())
