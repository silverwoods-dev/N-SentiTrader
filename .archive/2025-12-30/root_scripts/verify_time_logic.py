
from datetime import datetime, timedelta

def verify_cutoff(pub_kst_str):
    pub_kst = datetime.strptime(pub_kst_str, '%Y-%m-%d %H:%M')
    # UTC is KST - 9h
    pub_utc = pub_kst - timedelta(hours=9)
    
    # Logic in SQL: published_at >= DATE::timestamp + interval '7 hours'
    # For a date D, news from (D-1) 16:00 KST to D 16:00 KST is included.
    # (D-1) 16:00 KST = (D-1) 07:00 UTC
    # D 16:00 KST = D 07:00 UTC
    
    print(f"KST: {pub_kst} -> UTC: {pub_utc}")
    
    # Target date D
    target_date = datetime(2025, 12, 22).date()
    start_utc = datetime.combine(target_date - timedelta(days=1), datetime.min.time()) + timedelta(hours=7)
    end_utc = datetime.combine(target_date, datetime.min.time()) + timedelta(hours=7)
    
    is_included = start_utc <= pub_utc < end_utc
    print(f"Target Date: {target_date}")
    print(f"Window UTC: {start_utc} to {end_utc}")
    print(f"Included? {is_included}")
    return is_included

if __name__ == "__main__":
    print("Case 1: 12-23 00:00 KST (The leaked case reported by user)")
    verify_cutoff("2025-12-23 00:00")
    
    print("\nCase 2: 12-22 15:59 KST (End of 12-22 window)")
    verify_cutoff("2025-12-22 15:59")
    
    print("\nCase 3: 12-21 16:01 KST (Start of 12-22 window)")
    verify_cutoff("2025-12-21 16:01")
