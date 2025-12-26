
from datetime import datetime, timedelta

def verify_final_cutoff():
    """Verify that the new cutoff correctly excludes post-market-open news"""
    
    # For 12-23 prediction
    target_date = datetime(2025, 12, 23).date()
    prev_date = datetime(2025, 12, 22).date()
    
    # SQL logic: prev_date + 7h to target_date + 0h
    start_utc = datetime.combine(prev_date, datetime.min.time()) + timedelta(hours=7)
    end_utc = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=0)
    
    start_kst = start_utc + timedelta(hours=9)
    end_kst = end_utc + timedelta(hours=9)
    
    print("=== News Window for 12-23 Prediction ===")
    print(f"Start (Prev close): {start_kst} KST ({start_utc} UTC)")
    print(f"End (Market open):  {end_kst} KST ({end_utc} UTC)")
    print()
    
    # Test cases
    test_cases = [
        ("2025-12-22 15:59", "Last minute before prev close"),
        ("2025-12-22 16:01", "Just after prev close - SHOULD INCLUDE"),
        ("2025-12-23 00:00", "Midnight news - SHOULD INCLUDE"),
        ("2025-12-23 08:59", "Last minute before market open - SHOULD INCLUDE"),
        ("2025-12-23 09:00", "Market open - SHOULD EXCLUDE"),
        ("2025-12-23 18:31", "Evening news (user's case) - SHOULD EXCLUDE"),
    ]
    
    for kst_str, desc in test_cases:
        pub_kst = datetime.strptime(kst_str, '%Y-%m-%d %H:%M')
        pub_utc = pub_kst - timedelta(hours=9)
        
        included = start_utc <= pub_utc < end_utc
        status = "✓ INCLUDED" if included else "✗ EXCLUDED"
        
        print(f"{status}: {kst_str} KST - {desc}")
    
if __name__ == "__main__":
    verify_final_cutoff()
