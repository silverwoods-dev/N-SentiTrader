import numpy as np
import polars as pl
from typing import List, Dict, Any

class TechIndicatorProvider:
    """
    주가 데이터를 기반으로 기술적 지표를 생성합니다.
    """
    
    @staticmethod
    def calculate_indicators(df: pl.DataFrame) -> pl.DataFrame:
        """
        RSI, MACD, SMA 등을 계산하여 반환
        입력 df: [date, return_rate, ...] (Ordered by date ASC)
        """
        if df.is_empty():
            return df
            
        # 1. Moving Averages (5, 20, 60)
        # return_rate 기반의 누적 수익률(또는 종가 복구)이 필요하지만, 
        # 여기서는 return_rate 자체의 이동평균을 사용하거나 
        # (만약 종가가 있다면 더 좋음)
        # daily_price Table에는 close_price가 있으므로 이를 활용하는 것이 정확함
        
        # 2. RSI (Relative Strength Index)
        def get_rsi(prices, period=14):
            deltas = np.diff(prices)
            gain = np.where(deltas > 0, deltas, 0)
            loss = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.zeros_like(prices)
            avg_loss = np.zeros_like(prices)
            
            # Simple moving average for initial RSI
            avg_gain[period] = np.mean(gain[:period])
            avg_loss[period] = np.mean(loss[:period])
            
            # Wilder's smoothing
            for i in range(period + 1, len(prices)):
                avg_gain[i] = (avg_gain[i-1] * (period - 1) + gain[i-1]) / period
                avg_loss[i] = (avg_loss[i-1] * (period - 1) + loss[i-1]) / period
                
            rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss!=0)
            rsi = 100 - (100 / (1 + rs))
            return rsi
            
        # 3. MACD
        def get_macd(prices, fast=12, slow=26, signal=9):
            def ema(p, n):
                alpha = 2 / (n + 1)
                res = np.zeros_like(p)
                res[0] = p[0]
                for i in range(1, len(p)):
                    res[i] = alpha * p[i] + (1 - alpha) * res[i-1]
                return res
            
            ema_fast = ema(prices, fast)
            ema_slow = ema(prices, slow)
            macd_line = ema_fast - ema_slow
            signal_line = ema(macd_line, signal)
            hist = macd_line - signal_line
            return macd_line, signal_line, hist

        # 데이터 확보 (close_price가 없는 경우 return_rate로 의사 가격 생성)
        if "close_price" in df.columns:
            prices = df["close_price"].cast(float).to_numpy()
        else:
            # return_rate 기반 누적 지수 생성
            returns = df["return_rate"].cast(float).to_numpy()
            prices = 100 * np.cumprod(1 + returns)
            
        # 계산 수행
        macd_l, macd_s, macd_h = get_macd(prices)
        rsi_14 = get_rsi(prices)
        
        # Polars 컬럼 추가
        df = df.with_columns([
            pl.Series(name="tech_rsi_14", values=rsi_14),
            pl.Series(name="tech_macd_line", values=macd_l),
            pl.Series(name="tech_macd_sig", values=macd_s),
            pl.Series(name="tech_macd_hist", values=macd_h)
        ])
        
        # 지연 지표 (T-1 시점의 지표가 T일 예측에 쓰여야 하므로 shift)
        tech_cols = ["tech_rsi_14", "tech_macd_line", "tech_macd_sig", "tech_macd_hist"]
        df = df.with_columns([
            pl.col(c).shift(1).fill_null(0.0).alias(c) for c in tech_cols
        ])
        
        return df

    @staticmethod
    def fetch_and_calculate(cur, stock_code, start_date, end_date):
        """DB에서 데이터를 가져와 지표 계산"""
        cur.execute("""
            SELECT date, close_price, return_rate 
            FROM tb_daily_price 
            WHERE stock_code = %s AND date BETWEEN %s AND %s
            ORDER BY date ASC
        """, (stock_code, start_date, end_date))
        rows = cur.fetchall()
        if not rows:
            return pl.DataFrame()
            
        df = pl.DataFrame(rows)
        return TechIndicatorProvider.calculate_indicators(df)
