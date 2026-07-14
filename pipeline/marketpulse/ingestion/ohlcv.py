"""
MarketPulseScan — OHLCV Ingestion Module

Fetches historical OHLCV data with parquet caching.
Primary: BhavcopProvider latest EOD prices
Full history: YFinanceProvider (batched, 13mo daily)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path  # noqa: TC003
from typing import Any

import pandas as pd

from marketpulse.config.settings import (
    OHLCV_CACHE_FILE,
    OHLCV_CACHE_MAX_AGE_H,
)

log = logging.getLogger(__name__)


def _cache_is_fresh(path: Path, max_age_h: float) -> bool:
    """Return True if the cache file exists and is younger than max_age_h hours."""
    if not path.exists():
        return False
    age_h = (time.time() - path.stat().st_mtime) / 3600
    return age_h < max_age_h


def fetch_ohlcv(
    symbols: list[str],
    *,
    period: str = "13mo",
    interval: str = "1d",
    cache_file: Path = OHLCV_CACHE_FILE,
    cache_max_age_h: float = OHLCV_CACHE_MAX_AGE_H,
    force_refresh: bool = False,
    provider: Any | None = None,
) -> pd.DataFrame:
    """
    Fetch historical OHLCV for a list of symbols with parquet caching.

    Args:
        symbols:         NSE ticker symbols (no .NS suffix).
        period:          yfinance-style period (default "13mo").
        interval:        Candle interval (default "1d").
        cache_file:      Parquet path for the cache (default from settings).
        cache_max_age_h: Cache TTL in hours (default from settings).
        force_refresh:   If True, bypass cache.
        provider:        Optional pre-built OHLCVProvider; defaults to
                         the ProviderChain from get_provider_chain().

    Returns:
        MultiIndex DataFrame with columns (field, symbol).
        Fields: Open, High, Low, Close, Volume.
        Returns empty DataFrame on total failure.
    """
    # Try cache
    if not force_refresh and _cache_is_fresh(cache_file, cache_max_age_h):
        try:
            df = pd.read_parquet(cache_file)
            log.info("OHLCV: loaded from cache (%s)", cache_file.name)
            # Filter to requested symbols if cache has more
            if isinstance(df.columns, pd.MultiIndex):
                cached_syms = set(df.columns.get_level_values(1))
                req_syms = set(symbols)
                if req_syms.issubset(cached_syms):
                    return df.loc[:, df.columns.get_level_values(1).isin(req_syms)]
                # Cache miss for some symbols — fall through to re-download
            else:
                return df
        except Exception as exc:
            log.warning("OHLCV: cache load failed (%s) — re-downloading", exc)

    # Fetch from provider
    if provider is None:
        from marketpulse.ingestion.providers import get_provider_chain

        provider = get_provider_chain()

    log.info("OHLCV: downloading %d symbols (period=%s)", len(symbols), period)
    fetched: pd.DataFrame = provider.fetch_ohlcv(symbols, period=period, interval=interval)

    if fetched.empty:
        log.warning("OHLCV: provider returned empty DataFrame")
        return fetched

    # Cache the result
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        fetched.to_parquet(cache_file)
        log.info("OHLCV: cached to %s", cache_file.name)
    except Exception as exc:
        log.warning("OHLCV: cache write failed: %s", exc)

    return pd.DataFrame(fetched)


def extract_close_series(ohlcv: pd.DataFrame, symbol: str) -> pd.Series:
    """
    Extract the Close price series for a single symbol from a MultiIndex DataFrame.
    Returns empty Series if symbol not found.
    """
    if ohlcv.empty:
        return pd.Series(dtype=float, name=symbol)
    try:
        if isinstance(ohlcv.columns, pd.MultiIndex):
            for sym_key in (symbol, f"{symbol}.NS"):
                if sym_key in ohlcv.columns.get_level_values(1):
                    series: pd.Series[Any] = ohlcv["Close"][sym_key].dropna()
                    return series
        else:
            if "Close" in ohlcv.columns:
                series = ohlcv["Close"].dropna()
                return series
    except (KeyError, TypeError):
        pass
    return pd.Series(dtype=float, name=symbol)


def compute_returns(
    close: pd.Series,
    *,
    periods: dict[str, int] | None = None,
) -> dict[str, float | None]:
    """
    Compute percentage returns for standard lookback periods.

    Args:
        close:   Daily close price Series (DatetimeIndex).
        periods: {label: trading_days} — defaults to standard timeframes.

    Returns:
        {label: pct_return or None}. None if insufficient data.
    """
    if periods is None:
        periods = {
            "1D": 1,
            "1W": 5,
            "2W": 10,
            "1M": 21,
            "3M": 63,
            "6M": 126,
            "12M": 252,
        }

    result: dict[str, float | None] = {}
    if close.empty:
        return {k: None for k in periods}

    last = close.iloc[-1]
    for label, n_days in periods.items():
        if len(close) > n_days:
            base = close.iloc[-(n_days + 1)]
            result[label] = round((last - base) / base * 100, 2) if base else None
        else:
            result[label] = None

    return result
