import pandas as pd
import logging

log = logging.getLogger("marketpulse.resampler")

def resample_to_weekly(daily_ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Resamples daily OHLCV MultiIndex DataFrame to Weekly.
    Week ends on Friday.
    """
    if daily_ohlcv.empty:
        return daily_ohlcv

    log.info("Resampling daily data to weekly timeframe...")
    
    # We define custom aggregation rules for OHLCV
    agg_dict = {}
    for col in daily_ohlcv.columns:
        field = col[0]
        if field == "Open":
            agg_dict[col] = "first"
        elif field == "High":
            agg_dict[col] = "max"
        elif field == "Low":
            agg_dict[col] = "min"
        elif field == "Close":
            agg_dict[col] = "last"
        elif field == "Volume":
            agg_dict[col] = "sum"
        else:
            agg_dict[col] = "last"

    # Resample by week ending Friday
    weekly_ohlcv = daily_ohlcv.resample("W-FRI").agg(agg_dict)
    weekly_ohlcv.dropna(how='all', inplace=True)
    return weekly_ohlcv


def resample_to_monthly(daily_ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Resamples daily OHLCV MultiIndex DataFrame to Monthly.
    Month ends on the last calendar day.
    """
    if daily_ohlcv.empty:
        return daily_ohlcv

    log.info("Resampling daily data to monthly timeframe...")
    
    agg_dict = {}
    for col in daily_ohlcv.columns:
        field = col[0]
        if field == "Open":
            agg_dict[col] = "first"
        elif field == "High":
            agg_dict[col] = "max"
        elif field == "Low":
            agg_dict[col] = "min"
        elif field == "Close":
            agg_dict[col] = "last"
        elif field == "Volume":
            agg_dict[col] = "sum"
        else:
            agg_dict[col] = "last"

    # Resample by month end
    monthly_ohlcv = daily_ohlcv.resample("ME").agg(agg_dict)
    monthly_ohlcv.dropna(how='all', inplace=True)
    return monthly_ohlcv
