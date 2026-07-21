"""
Unit tests for technical/resampler.py — daily to weekly/monthly resampling.
"""

from __future__ import annotations

import pandas as pd
import pytest

from marketpulse.technical.resampler import resample_to_monthly, resample_to_weekly


@pytest.fixture
def sample_daily_ohlcv() -> pd.DataFrame:
    # Creating daily data for two weeks (10 trading days: Monday-Friday)
    dates = pd.date_range("2026-07-06", periods=12, freq="D")  # Mon 6 July to Fri 17 July

    # We want a MultiIndex columns structure: (field, symbol)
    columns = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume"], ["RELIANCE"]])

    # Fill in dummy values
    data = []
    for i in range(12):
        val = 100.0 + i
        # Open, High, Low, Close, Volume
        data.append([val, val + 5, val - 5, val + 2, 1000])

    df = pd.DataFrame(data, index=dates, columns=columns)
    # Filter to only keep business days (Mon-Fri)
    return df[df.index.dayofweek < 5]


def test_resample_to_weekly(sample_daily_ohlcv: pd.DataFrame) -> None:
    weekly = resample_to_weekly(sample_daily_ohlcv)

    assert len(weekly) == 2  # 2 weeks

    # Week 1: Mon 6 July to Fri 10 July
    # Open should be the first open, Close should be the last close
    assert weekly[("Open", "RELIANCE")].iloc[0] == 100.0
    assert weekly[("Close", "RELIANCE")].iloc[0] == 106.0
    assert weekly[("Volume", "RELIANCE")].iloc[0] == 5000.0


def test_resample_to_monthly(sample_daily_ohlcv: pd.DataFrame) -> None:
    monthly = resample_to_monthly(sample_daily_ohlcv)

    # All daily data is within July, so it should resample to 1 month
    assert len(monthly) == 1
    assert monthly[("Open", "RELIANCE")].iloc[0] == 100.0
    assert monthly[("Volume", "RELIANCE")].iloc[0] == 10000.0  # 10 business days


def test_resample_empty() -> None:
    df = pd.DataFrame()
    assert resample_to_weekly(df).empty
    assert resample_to_monthly(df).empty
