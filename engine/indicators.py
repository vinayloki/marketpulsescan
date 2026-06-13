import pandas as pd
import numpy as np

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Calculates Simple Moving Average."""
    return series.rolling(window=period, min_periods=1).mean()

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculates Exponential Moving Average."""
    return series.ewm(span=period, adjust=False, min_periods=1).mean()

def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index using Wilder's Smoothing."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # Fill initial NaNs or infs
    rsi = rsi.replace([np.inf, -np.inf], 100).fillna(50)
    return rsi

def get_trend_slope(series: pd.Series, lookback: int = 5) -> pd.Series:
    """
    Calculates the slope of a series over the last `lookback` periods.
    Positive value means rising, negative means falling.
    Useful for checking if a moving average is rising.
    """
    # Simple rate of change % over lookback periods
    return series.pct_change(periods=lookback) * 100

def check_rising(series: pd.Series, lookback: int = 5) -> bool:
    """
    Returns True if the series value is higher than it was `lookback` periods ago.
    """
    if len(series) <= lookback:
        return False
    return float(series.iloc[-1]) > float(series.iloc[-(lookback + 1)])
