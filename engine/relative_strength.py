import pandas as pd
import logging
import numpy as np

log = logging.getLogger("marketpulse.rs")

def calculate_rs_rating(ohlcv: pd.DataFrame, benchmark_ticker: str = "^NSEI") -> pd.Series:
    """
    Calculates a 0-100 Relative Strength (RS) Rating for all stocks in the OHLCV DataFrame.
    Similar to IBD's RS Rating.
    
    RS Score Formula (Weighted Return):
    40% * 3-month return
    20% * 6-month return
    20% * 9-month return
    20% * 12-month return
    
    The resulting composite scores are then ranked and converted to a percentile (0-100).
    """
    if "Close" not in ohlcv.columns.get_level_values(0):
        log.warning("No 'Close' column found. Cannot calculate RS Rating.")
        return pd.Series(dtype=float)

    close_df = ohlcv["Close"]
    tickers = close_df.columns.tolist()

    if len(close_df) < 252:
        log.warning("Insufficient data for 12-month RS calculation (need 252 days).")
        # Fallback to a shorter duration calculation if needed, but for now we require 1y data.
    
    # Calculate returns for 63 days (3mo), 126 days (6mo), 189 days (9mo), 252 days (12mo)
    # Using shift to get the price N periods ago.
    
    rs_raw = {}
    for ticker in tickers:
        series = close_df[ticker].dropna()
        if len(series) < 252:
            rs_raw[ticker] = np.nan
            continue
            
        current_close = series.iloc[-1]
        
        # Safe extraction of past prices
        close_3m = series.iloc[-63] if len(series) >= 63 else series.iloc[0]
        close_6m = series.iloc[-126] if len(series) >= 126 else series.iloc[0]
        close_9m = series.iloc[-189] if len(series) >= 189 else series.iloc[0]
        close_12m = series.iloc[-252] if len(series) >= 252 else series.iloc[0]
        
        ret_3m = (current_close - close_3m) / close_3m
        ret_6m = (current_close - close_6m) / close_6m
        ret_9m = (current_close - close_9m) / close_9m
        ret_12m = (current_close - close_12m) / close_12m
        
        # Composite Weighted Return
        composite = (0.4 * ret_3m) + (0.2 * ret_6m) + (0.2 * ret_9m) + (0.2 * ret_12m)
        rs_raw[ticker] = composite

    # Convert to pandas Series
    raw_series = pd.Series(rs_raw).dropna()
    
    if raw_series.empty:
        return raw_series

    # Calculate percentile rank (0 to 100)
    rs_rating = raw_series.rank(pct=True) * 100
    
    log.info(f"Calculated RS Ratings for {len(rs_rating)} stocks.")
    return rs_rating.round(2)
