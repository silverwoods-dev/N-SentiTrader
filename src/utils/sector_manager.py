
import logging
import pandas as pd
from pykrx import stock
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SectorManager:
    # Mapping sector_code to pykrx index tickers
    # IT_SEMICON -> KRX Semiconductor (5044)
    # IT_SERVICE -> KOSPI IT Service (1046)
    # E_E -> KOSPI Electrical & Electronics (1013)
    SECTOR_INDEX_MAP = {
        'IT_SEMICON': '5044',
        'IT_SERVICE': '1046',
        'E_E': '1013',
    }

    @classmethod
    def get_sector_return(cls, sector_code: str, target_date: datetime.date):
        """
        Fetch the sector return for a specific date using standard indices.
        If sector_code is not mapped, returns 0.0.
        """
        index_ticker = cls.SECTOR_INDEX_MAP.get(sector_code)
        if not index_ticker:
            logger.warning(f"Sector code {sector_code} not mapped to any index.")
            return 0.0

        try:
            start_date = (target_date - timedelta(days=5)).strftime('%Y%m%d')
            end_date = target_date.strftime('%Y%m%d')
            
            # Note: We need to determine if it's a KOSPI, KOSDAQ, or KRX index.
            # Pykrx get_index_ohlcv_by_date doesn't strictly require market if unique.
            df = stock.get_index_ohlcv_by_date(fromdate=start_date, todate=end_date, ticker=index_ticker)
            
            if df.empty:
                logger.warning(f"No index data for {index_ticker} on {target_date}")
                return 0.0
            
            target_ts = pd.Timestamp(target_date)
            if target_ts not in df.index:
                logger.warning(f"Index data for {target_date} not available yet.")
                return 0.0
            
            idx = df.index.get_loc(target_ts)
            if idx == 0:
                logger.warning(f"Insufficient history for index {index_ticker}")
                return 0.0
            
            close = float(df.iloc[idx]['종가'])
            prev_close = float(df.iloc[idx-1]['종가'])
            return_rate = (close / prev_close) - 1
            return return_rate

        except Exception as e:
            logger.error(f"Error fetching sector return for {sector_code}: {e}")
            return 0.0
