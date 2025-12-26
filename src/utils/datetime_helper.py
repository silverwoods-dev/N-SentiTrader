# src/utils/datetime_helper.py
"""
Safe datetime handling utilities for mixed-precision datetime data.
Handles both legacy (date-only, 00:00) and precise datetime values.
"""
from datetime import datetime, timedelta, time

def is_date_only(dt):
    """Check if datetime is date-only (00:00:00)."""
    if not dt:
        return True
    if isinstance(dt, datetime):
        return dt.hour == 0 and dt.minute == 0 and dt.second == 0
    return False

def safe_datetime_diff_hours(later_dt, earlier_dt, default_hours=24.0):
    """
    Calculate hours difference between two datetimes safely.
    
    Args:
        later_dt: Later datetime (e.g., market open)
        earlier_dt: Earlier datetime (e.g., news published_at) - may be None or date-only
        default_hours: Default value if earlier_dt is None or date-only
    
    Returns:
        float: Hours difference
    """
    if not earlier_dt:
        return default_hours
    
    try:
        if isinstance(earlier_dt, str):
            earlier_dt = datetime.fromisoformat(earlier_dt)
        
        # If earlier_dt is date-only (00:00:00), use default
        if is_date_only(earlier_dt):
            return default_hours
        
        diff_seconds = (later_dt - earlier_dt).total_seconds()
        return max(0, diff_seconds / 3600.0)
    except Exception:
        return default_hours

def format_datetime_for_display(dt, fallback_to_date=True):
    """
    Format datetime for user display.
    
    Args:
        dt: datetime object (may be None or date-only)
        fallback_to_date: If True and dt is date-only, show only date
    
    Returns:
        str: Formatted string
    """
    if not dt:
        return ""
    
    try:
        # Convert to KST (+9 hours)
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        
        kst_dt = dt + timedelta(hours=9)
        
        # If date-only, show just the date
        if fallback_to_date and is_date_only(kst_dt):
            return kst_dt.strftime('%Y-%m-%d')
        
        return kst_dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return str(dt) if dt else ""

def safe_time_decay(target_dt, published_dt, decay_rate=0.02, default_weight=1.0):
    """
    Calculate time-based decay weight safely.
    
    Args:
        target_dt: Target datetime (e.g., market open)
        published_dt: Published datetime (may be None or date-only)
        decay_rate: Decay rate (default 0.02 for e^(-0.02*hours))
        default_weight: Default weight if published_dt is invalid
    
    Returns:
        float: Decay weight (0.0 to 1.0)
    """
    import math
    
    hours_diff = safe_datetime_diff_hours(target_dt, published_dt, default_hours=24.0)
    
    try:
        weight = math.exp(-decay_rate * hours_diff)
        return max(0.0, min(1.0, weight))
    except Exception:
        return default_weight
