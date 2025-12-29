# src/dashboard/filters.py
from datetime import timedelta

def format_kst(dt, fmt='%Y-%m-%d %H:%M:%S'):
    if not dt:
        return "-"
    if isinstance(dt, str):
        return dt
    kst_dt = dt + timedelta(hours=9)
    return kst_dt.strftime(fmt)
