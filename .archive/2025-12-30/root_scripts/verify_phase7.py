from src.utils import calendar_helper
from datetime import datetime, timedelta

def verify_phase7():
    print("--- Phase 7 Calendar Verification ---")
    
    # 1. Check Dec 25th (Christmas)
    christmas = "2025-12-25"
    is_open = calendar_helper.is_trading_day(christmas)
    status = calendar_helper.get_market_status(christmas)
    print(f"Date: {christmas} | Is Trading Day: {is_open} | Status: {status}")
    
    # 2. Check Dec 26th (Friday)
    friday = "2025-12-26"
    is_open_fri = calendar_helper.is_trading_day(friday)
    print(f"Date: {friday} | Is Trading Day: {is_open_fri}")
    
    # 3. Check Dec 31st (KRX Year-end holiday)
    yearend = "2025-12-31"
    is_open_ye = calendar_helper.is_trading_day(yearend)
    print(f"Date: {yearend} | Is Trading Day: {is_open_ye} (Expected False for KRX)")

    # 4. Check trading days list
    days = calendar_helper.get_trading_days("2025-12-22", days=5)
    print(f"Trading days from 12/22 (5 days): {days}")
    # Expected: 22, 23, 24, 26, 29 (25 skipped)

    if not is_open and is_open_fri:
        print("\nSUCCESS: Calendar correctly identifies 12/25 as holiday and 12/26 as trading day.")
    else:
        print("\nFAILURE: Calendar logic check failed.")

if __name__ == "__main__":
    verify_phase7()
