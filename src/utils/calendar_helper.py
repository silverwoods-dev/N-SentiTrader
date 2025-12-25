import exchange_calendars as ecals
import pandas as pd
from datetime import datetime, timedelta
import pytz

def get_krx_calendar():
    """Returns the KRX exchange calendar."""
    return ecals.get_calendar("XKRX")

def get_trading_days(start_date=None, days=10):
    """
    Returns the next N trading days from start_date (inclusive if it's a trading day).
    """
    krx = get_krx_calendar()
    
    if start_date is None:
        start_date = datetime.now()
        
    # Convert to pandas timestamp
    start_ts = pd.Timestamp(start_date).tz_localize(None)
    
    # Get a range of days (safety margin of 30 days to find 10 trading days)
    end_ts = start_ts + timedelta(days=30)
    
    sessions = krx.sessions_in_range(start_ts, end_ts)
    
    # Return as list of strings YYYY-MM-DD
    return [s.strftime('%Y-%m-%d') for s in sessions[:days]]

def is_trading_day(date_str):
    """Checks if a given date string is a KRX trading day."""
    krx = get_krx_calendar()
    try:
        dt = pd.Timestamp(date_str).tz_localize(None)
        return krx.is_session(dt)
    except:
        return False

def get_market_status(date_str):
    """
    Returns 'OPEN' or 'CLOSED' for a given date.
    Note: In Phase 7, we'll use this to label 12/25 as 'CLOSED'.
    """
    if is_trading_day(date_str):
        return "OPEN"
    return "CLOSED"
