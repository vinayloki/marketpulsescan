"""
MarketPulseScan — YFinance Provider (Fallback)

Provides:
  - Full historical OHLCV (13mo daily, batched)
  - Fundamental data (.info)
  - Universe fallback via Wikipedia NIFTY tables

Declared capabilities: {"ohlcv", "fundamentals", "universe"}
"""

from __future__ import annotations

import logging
import time
from typing import Any, ClassVar

import pandas as pd

from marketpulse.config.settings import (
    BATCH_DELAY_SECONDS,
    BATCH_SIZE,
    MIN_DATA_POINTS,
)

log = logging.getLogger(__name__)


class YFinanceProvider:
    """
    Fallback provider using yfinance.

    Ported from legacy data_providers/yfinance_provider.py and the
    OHLCV download logic in NSEDirectProvider with:
      - Type annotations
      - Configurable batch size / delay (from settings)
      - Capability flags for ProviderChain routing
    """

    capabilities: frozenset[str] = frozenset({"ohlcv", "fundamentals", "universe"})

    _NIFTY_WIKI_URLS: ClassVar[list[str]] = [
        "https://en.wikipedia.org/wiki/NIFTY_500",
        "https://en.wikipedia.org/wiki/NIFTY_100",
        "https://en.wikipedia.org/wiki/NIFTY_50",
    ]

    def __init__(
        self,
        batch_size: int = BATCH_SIZE,
        batch_delay: float = BATCH_DELAY_SECONDS,
        min_data_points: int = MIN_DATA_POINTS,
    ) -> None:
        self._batch_size = batch_size
        self._batch_delay = batch_delay
        self._min_points = min_data_points

    # ── Universe ──────────────────────────────────────────────────────────────

    def fetch_universe(self) -> list[str]:
        """
        Build universe from Wikipedia NIFTY tables as fallback.
        Returns up to ~500 well-known NSE tickers.
        """
        log.info("YFinanceProvider: fetching universe from Wikipedia tables")
        tickers: set[str] = set()

        for url in self._NIFTY_WIKI_URLS:
            try:
                tables = pd.read_html(url)
                for table in tables:
                    cols = [str(c).upper() for c in table.columns]
                    sym_col = next(
                        (c for c in cols if "SYMBOL" in c or "TICKER" in c),
                        None,
                    )
                    if sym_col is None:
                        continue
                    idx = cols.index(sym_col)
                    syms = table.iloc[:, idx].dropna().astype(str).str.strip().str.upper()
                    tickers.update(s for s in syms if s and not s.isdigit())
                if len(tickers) > 100:
                    break
            except Exception as exc:
                log.debug("YFinanceProvider: Wikipedia parse failed for %s: %s", url, exc)
                continue

        result = sorted(tickers)
        log.info("YFinanceProvider: %d tickers from Wikipedia fallback", len(result))
        return result

    # ── OHLCV ─────────────────────────────────────────────────────────────────

    def fetch_ohlcv(
        self,
        symbols: list[str],
        *,
        period: str = "13mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Download historical OHLCV for given symbols in batches.

        Returns MultiIndex DataFrame: columns = (field, symbol).
        Fields: Open, High, Low, Close, Volume.
        Silently drops symbols with fewer than min_data_points rows.
        Returns empty DataFrame on total failure.
        """
        try:
            import yfinance as yf
        except ImportError:
            log.error("YFinanceProvider: yfinance not installed")
            return pd.DataFrame()

        # Convert plain NSE symbols to yfinance format (append .NS)
        yf_symbols = [f"{s}.NS" if not s.endswith((".NS", ".BO")) else s for s in symbols]
        all_frames: list[pd.DataFrame] = []

        for i in range(0, len(yf_symbols), self._batch_size):
            batch = yf_symbols[i : i + self._batch_size]
            log.debug(
                "YFinanceProvider: downloading batch %d-%d of %d",
                i + 1,
                min(i + self._batch_size, len(yf_symbols)),
                len(yf_symbols),
            )
            try:
                raw = yf.download(
                    batch,
                    period=period,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    group_by="ticker",
                )
                if not raw.empty:
                    all_frames.append(raw)
            except Exception as exc:
                log.warning("YFinanceProvider: batch %d failed: %s", i // self._batch_size + 1, exc)

            if i + self._batch_size < len(yf_symbols):
                time.sleep(self._batch_delay)

        if not all_frames:
            log.warning("YFinanceProvider: all OHLCV batches failed")
            return pd.DataFrame()

        combined = pd.concat(all_frames, axis=1) if len(all_frames) > 1 else all_frames[0]

        # Drop symbols with insufficient data
        if isinstance(combined.columns, pd.MultiIndex):
            valid_syms = []
            for sym in combined.columns.get_level_values(1).unique():
                sym_data = combined.xs(sym, axis=1, level=1, drop_level=False)
                if len(sym_data.dropna(how="all")) >= self._min_points:
                    valid_syms.append(sym)
            combined = combined.loc[:, combined.columns.get_level_values(1).isin(valid_syms)]

        return combined

    # ── Fundamentals ──────────────────────────────────────────────────────────

    def fetch_fundamentals(
        self,
        symbols: list[str],
    ) -> dict[str, dict[str, Any]]:
        """
        Fetch fundamental data for each symbol using yfinance .info.

        Returns {symbol: {field: value}}. Missing fields are None.
        Never raises — returns {} on total failure.
        """
        try:
            import yfinance as yf
        except ImportError:
            log.error("YFinanceProvider: yfinance not installed")
            return {}

        result: dict[str, dict[str, Any]] = {}
        for sym in symbols:
            yf_sym = f"{sym}.NS" if not sym.endswith((".NS", ".BO")) else sym
            try:
                info: dict[str, Any] = yf.Ticker(yf_sym).info or {}
                result[sym] = {
                    "name": info.get("longName") or info.get("shortName"),
                    "sector": info.get("sector"),
                    "industry": info.get("industry"),
                    "mcap": info.get("marketCap"),
                    "pe": info.get("trailingPE"),
                    "pb": info.get("priceToBook"),
                    "eps": info.get("trailingEps"),
                    "roe": info.get("returnOnEquity"),
                    "52h": info.get("fiftyTwoWeekHigh"),
                    "52l": info.get("fiftyTwoWeekLow"),
                    "bv": info.get("bookValue"),
                    "dy": info.get("dividendYield"),
                    "debt_eq": info.get("debtToEquity"),
                    "mcap_cr": (info.get("marketCap") or 0) / 1e7,  # INR -> crore
                }
            except Exception as exc:
                log.debug("YFinanceProvider: fundamentals failed for %s: %s", sym, exc)
                result[sym] = {}

        return result
