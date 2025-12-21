# src/dashboard/filters.py
from datetime import timedelta

def format_kst(dt):
    if not dt:
        return "-"
    if isinstance(dt, str):
        return dt
    kst_dt = dt + timedelta(hours=9)
    return kst_dt.strftime('%Y-%m-%d %H:%M:%S')
