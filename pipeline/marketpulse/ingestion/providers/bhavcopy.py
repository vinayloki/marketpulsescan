"""
MarketPulseScan — Bhavcopy Provider (Primary)

Uses the `nse-archives` package to fetch:
  - NSE equity universe (EQ series from daily bhavcopy)
  - Latest daily bhavcopy OHLCV (current day's EOD prices)

Declared capabilities: {"universe", "bhavcopy"}
Note: Full historical OHLCV (13mo) is NOT supported here —
      that responsibility belongs to YFinanceProvider.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

log = logging.getLogger(__name__)

# Try importing the nse-archives library (imported as `nsedata`)
_nse_api: Any = None
_NSE_AVAILABLE = False
try:
    from nsedata import nse as _nse_api

    _NSE_AVAILABLE = True
except ImportError:
    log.warning("nse-archives package not installed — BhavcopProvider will degrade")


class BhavcopProvider:
    """
    Primary data provider using NSE Archives (official bhavcopy).

    Ported from legacy data_providers/nse_archives_provider.py with:
      - Type annotations
      - Structured error handling
      - Capability flags for ProviderChain routing
    """

    capabilities: frozenset[str] = frozenset({"universe", "bhavcopy"})

    def __init__(self, lookback_days: int = 6) -> None:
        self._lookback_days = lookback_days
        self._api = _nse_api if _NSE_AVAILABLE else None

    # ── Universe ──────────────────────────────────────────────────────────────

    def fetch_universe(self) -> list[str]:
        """
        Fetch all NSE equity tickers using the latest available Bhavcopy.
        Filters for EQ series only. Returns sorted list, empty on failure.
        """
        if not self._api:
            log.warning("BhavcopProvider: nse-archives unavailable for universe fetch")
            return []

        df = self._fetch_latest_bhavcopy()
        if df.empty:
            return []

        sym_col = self._find_col(df, ["SYMBOL", "TKT_NAME", "INSTRUMENT"])
        srs_col = self._find_col(df, ["SERIES", "SCTYSRS"])

        if not sym_col:
            log.warning("BhavcopProvider: no SYMBOL column found in bhavcopy")
            return []

        # Filter EQ series only
        if srs_col:
            df = df[df[srs_col].astype(str).str.strip().str.upper() == "EQ"]

        tickers = df[sym_col].dropna().astype(str).str.strip().str.upper().unique().tolist()
        tickers = sorted([t for t in tickers if t and not t.isdigit() and "NIFTY" not in t])

        log.info("BhavcopProvider: %d equity tickers from bhavcopy", len(tickers))
        return tickers

    # ── Bhavcopy OHLCV (single day) ───────────────────────────────────────────

    def fetch_latest_bhavcopy(self, date: datetime | None = None) -> pd.DataFrame:
        """
        Download a single day's Bhavcopy as a normalised DataFrame.

        Looks back up to `lookback_days` to find the most recent trading day.
        Returns empty DataFrame on failure.

        Columns in returned DataFrame (standardised):
            symbol, open, high, low, close, volume, series, date
        """
        raw = self._fetch_latest_bhavcopy(date)
        if raw.empty:
            return pd.DataFrame()
        return self._normalise_bhavcopy(raw)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _fetch_latest_bhavcopy(self, date: datetime | None = None) -> pd.DataFrame:
        """Raw bhavcopy fetch — returns un-normalised DataFrame."""
        if not self._api:
            return pd.DataFrame()

        dates_to_try: list[str] = []
        if date:
            dates_to_try = [date.strftime("%Y-%m-%d")]
        else:
            dates_to_try = [
                (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(self._lookback_days)
            ]

        for dt_str in dates_to_try:
            try:
                df: pd.DataFrame = self._api.get(
                    "capital_market", "equities_sme", "sec_bhavdata_full", dt_str
                )
                if df is not None and not df.empty:
                    log.info("BhavcopProvider: bhavcopy loaded for %s (%d rows)", dt_str, len(df))
                    return df
            except Exception as exc:
                log.debug("BhavcopProvider: bhavcopy attempt %s failed: %s", dt_str, exc)
                continue

        log.warning(
            "BhavcopProvider: could not load bhavcopy for last %d days", self._lookback_days
        )
        return pd.DataFrame()

    def _normalise_bhavcopy(self, raw: pd.DataFrame) -> pd.DataFrame:
        """
        Map raw bhavcopy columns to standardised schema.
        Filters to EQ series. Returns empty DataFrame if mapping fails.
        """
        # Filter EQ series
        srs_col = self._find_col(raw, ["SERIES", "SCTYSRS"])
        if srs_col:
            raw = raw[raw[srs_col].astype(str).str.strip().str.upper() == "EQ"].copy()

        sym_col = self._find_col(raw, ["SYMBOL", "TKT_NAME"])
        open_col = self._find_col(raw, ["OPEN_PRICE", "OPEN", "OP"])
        high_col = self._find_col(raw, ["HIGH_PRICE", "HIGH", "HP"])
        low_col = self._find_col(raw, ["LOW_PRICE", "LOW", "LP"])
        close_col = self._find_col(raw, ["CLOSE_PRICE", "CLOSE", "CP", "LAST_PRICE"])
        vol_col = self._find_col(raw, ["TTL_TRD_QNTY", "VOLUME", "TOTTRDQTY", "QTY"])

        if not sym_col or not close_col:
            log.warning("BhavcopProvider: could not map required columns in bhavcopy")
            return pd.DataFrame()

        out = pd.DataFrame()
        out["symbol"] = raw[sym_col].astype(str).str.strip().str.upper()
        out["close"] = pd.to_numeric(raw[close_col], errors="coerce")
        if open_col:
            out["open"] = pd.to_numeric(raw[open_col], errors="coerce")
        if high_col:
            out["high"] = pd.to_numeric(raw[high_col], errors="coerce")
        if low_col:
            out["low"] = pd.to_numeric(raw[low_col], errors="coerce")
        if vol_col:
            out["volume"] = pd.to_numeric(raw[vol_col], errors="coerce")

        return out.dropna(subset=["symbol", "close"]).reset_index(drop=True)

    @staticmethod
    def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
        """Return the first matching column name (case-insensitive) from candidates."""
        upper_cols = {c.upper(): c for c in df.columns}
        for candidate in candidates:
            if candidate.upper() in upper_cols:
                return upper_cols[candidate.upper()]
        return None
