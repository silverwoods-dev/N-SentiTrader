import pytest
from playwright.sync_api import Page, expect
import re

# 대시보드 URL (컨테이너 환경 고려)
DASHBOARD_URL = "http://localhost:8080"

def test_dashboard_loading(page: Page):
    page.goto(DASHBOARD_URL)
    expect(page).to_have_title("Dashboard - N-SentiTrader")

def test_bento_grid_layout(page: Page):
    page.goto(DASHBOARD_URL)
    grid = page.locator(".grid")
    expect(grid.first).to_be_visible()
    expect(page.get_by_text("Add Daily Target")).to_be_visible()
    expect(page.get_by_text("System Status")).to_be_visible()
    expect(page.get_by_text("Active & Recent Jobs")).to_be_visible()
    expect(page.get_by_text("Daily Targets")).to_be_visible()

def test_htmx_polling_setup(page: Page):
    page.goto(DASHBOARD_URL)
    jobs_polling = page.locator("[hx-get='/jobs/list']")
    expect(jobs_polling).to_have_attribute("hx-trigger", "every 2s")
    stocks_polling = page.locator("[hx-get='/targets/list']")
    expect(stocks_polling).to_have_attribute("hx-trigger", "every 5s")

def test_toast_close_button(page: Page):
    page.goto(DASHBOARD_URL)
    
    # Console log capture
    page.on("console", lambda msg: print(f"BROWSER CONSOLE: {msg.text}"))
    
    # 'Add Stock' 폼 제출
    # '005930'이 이미 있을 수 있으므로 매번 다른 코드를 사용하거나 상관없이 제출
    import random
    code = f"{random.randint(100000, 999999)}"
    print(f"Adding Stock code: {code}")
    
    page.fill("input[name='stock_code']", code)
    print("Clicking Add Stock button...")
    page.click("button:has-text('Add Stock')")
    
    # Toast가 나타날 때까지 대기
    print("Waiting for toast...")
    # HTMX request might take time
    toast = page.locator("#toast-container > div")
    
    # We wait for the toast to appear
    try:
        expect(toast.first).to_be_visible(timeout=10000)
        print("Toast is visible!")
    except Exception as e:
        print(f"Toast did not appear! Current page content snippet: {page.content()[:500]}")
        raise e
    
    close_button = toast.first.locator("button")
    expect(close_button).to_be_visible()
    
    print("Clicking close button...")
    # Toast close button click might need a bit of time for animation
    close_button.click()
    expect(toast.first).not_to_be_visible()
    print("Toast closed successfully!")

def test_delete_modal_interaction(page: Page):
    page.goto(DASHBOARD_URL)
    
    # Job 테이블의 첫 번째 삭제 버튼 대기
    print("Waiting for job delete button...")
    delete_button = page.locator("#job-list-body button[title='Delete']").first
    
    # 만약 버튼이 없으면 하나 추가하거나 건너뜀 (여기서는 있다고 가정)
    expect(delete_button).to_be_visible(timeout=10000)
    
    print("Clicking delete button...")
    delete_button.click()
    
    print("Checking modal visibility...")
    modal = page.locator("#modal-container")
    expect(modal).not_to_have_class("hidden")
    expect(modal).to_be_visible()
    
    expect(page.get_by_text("Confirm Deletion")).to_be_visible()
    
    print("Clicking Cancel...")
    page.get_by_role("button", name="Cancel").click()
    
    expect(modal).to_have_class(re.compile(r".*hidden.*"))
    expect(modal).not_to_be_visible()
    print("Modal closed successfully!")

def test_target_delete_interaction(page: Page):
    page.goto(DASHBOARD_URL)
    
    # Target 테이블의 첫 번째 삭제 버튼 대기
    print("Waiting for target delete button...")
    delete_button = page.locator("#stock-list-body button[title='Delete']").first
    
    # 만약 버튼이 없으면 하나 추가 (Add Stock)
    if not delete_button.is_visible():
        print("No targets found, adding one...")
        page.fill("input[name='stock_code']", "005930")
        page.click("button:has-text('Add Stock')")
        expect(delete_button).to_be_visible(timeout=10000)
    
    expect(delete_button).to_be_visible()
    delete_button.click()
    
    modal = page.locator("#modal-container")
    expect(modal).to_be_visible()
    expect(page.get_by_text("Confirm Deletion")).to_be_visible()
    
    # 실제 삭제 버튼 클릭 (Confirm)
    print("Clicking Confirm Delete...")
    page.locator("#confirm-delete-btn").click()
    
    expect(modal).not_to_be_visible()
    # Toast 확인
    toast = page.locator("#toast-container > div")
    expect(toast.first).to_be_visible()
    expect(toast.first).to_contain_text("Target deleted")
    print("Target deletion UI test passed!")

def test_target_auto_activate_toggle(page: Page):
    page.goto(DASHBOARD_URL)
    
    # Target 테이블 대기
    print("Waiting for target row...")
    row = page.locator("#stock-list-body tr").first
    
    if not row.is_visible():
        print("No targets found, adding one...")
        page.fill("input[name='stock_code']", "005930")
        page.click("button:has-text('Add Stock')")
        expect(row).to_be_visible(timeout=10000)

    toggle_btn = row.locator("button[title='Auto Activate after Backfill']")
    expect(toggle_btn).to_be_visible()
    
    # 텍스트 확인 (On/Off)
    status_text = toggle_btn.locator("span").text_content().strip().lower()
    print(f"Initial auto-activate status: {status_text}")
    
    # 클릭
    toggle_btn.click()
    
    # 상태값 변경 대기 (HTMX)
    new_status_text = "off" if status_text == "on" else "on"
    expect(toggle_btn.locator("span")).to_contain_text(new_status_text, timeout=5000)
    print(f"New auto-activate status: {new_status_text}")
    
    # 다시 클릭해서 원복
    toggle_btn.click()
    expect(toggle_btn.locator("span")).to_contain_text(status_text, timeout=5000)
    print("Auto-activate toggle test passed!")
