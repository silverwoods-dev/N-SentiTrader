# src/utils/calendar.py
from datetime import datetime, date, timedelta
from src.db.connection import get_db_cursor
import logging

logger = logging.getLogger(__name__)

class Calendar:
    _trading_days_cache = {}

    @classmethod
    def get_trading_days(cls, stock_code, start_date=None, end_date=None):
        """특정 종목의 거래일 목록을 가져옵니다 (tb_daily_price 기반)"""
        if stock_code in cls._trading_days_cache:
            # Simple cache for performance within a single run
            # In a long-running process, this might need more robust invalidation
            return cls._trading_days_cache[stock_code]

        with get_db_cursor() as cur:
            cur.execute("""
                SELECT DISTINCT date FROM tb_daily_price 
                WHERE stock_code = %s
                ORDER BY date ASC
            """, (stock_code,))
            rows = cur.fetchall()
            days = [r['date'] for r in rows]
            cls._trading_days_cache[stock_code] = days
            return days

    @classmethod
    def get_next_trading_day(cls, stock_code, target_date):
        """target_date 이후(포함)의 첫 번째 거래일을 반환합니다."""
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        days = cls.get_trading_days(stock_code)
        for d in days:
            if d >= target_date:
                return d
        
        # 만약 DB에 미래 데이터가 없다면, 가상의 다음 영업일 반환 (단순화: 주말 제외)
        curr = target_date
        while True:
            if curr.weekday() < 5: # Mon-Fri
                return curr
            curr += timedelta(days=1)

    @classmethod
    def get_impact_date(cls, stock_code, published_at):
        """
        뉴스 발행 시각을 기준으로 해당 뉴스가 어느 거래일의 주가에 영향을 줄지 결정합니다.
        기본 로직: 당일 장 시작 전/장 중 뉴스는 당일, 장 마감 후/주말 뉴스는 다음 거래일.
        (현재는 시간 정보가 부족할 수 있으므로 날짜 기준으로만 판단: 당일 혹은 다음 거래일)
        """
        if isinstance(published_at, datetime):
            p_date = published_at.date()
            p_hour = published_at.hour
        else:
            p_date = published_at
            p_hour = 12 # Default to midday if time is missing
            
        # 장 마감(15:30) 이후 뉴스는 다음 거래일로 할당
        if p_hour >= 16:
            p_date += timedelta(days=1)
            
        return cls.get_next_trading_day(stock_code, p_date)

    @classmethod
    def is_trading_day(cls, stock_code, target_date):
        if isinstance(target_date, str):
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        days = cls.get_trading_days(stock_code)
        return target_date in days
