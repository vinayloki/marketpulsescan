"""
MarketPulse India — Base Data Provider (Abstract Interface)

All data providers must implement this contract.
Swap providers without touching scanner or engine code.
"""

from abc import ABC, abstractmethod
import pandas as pd


class BaseDataProvider(ABC):
    """
    Abstract base class defining the data layer contract.

    Implementations:
        - NSEDirectProvider  (primary, NSE CSV + yfinance OHLCV)
        - YFinanceProvider   (fallback, pure yfinance)

    Extension guide:
        To add a new provider (e.g. Zerodha, Upstox):
        1. Subclass BaseDataProvider
        2. Implement all three abstract methods
        3. Register it in data_providers/__init__.py get_provider()
    """

    # ── Universe ──────────────────────────────────────────────────────

    @abstractmethod
    def fetch_ticker_universe(self) -> list[str]:
        """
        Return a list of valid NSE equity ticker symbols (without .NS suffix).

        Example return: ["RELIANCE", "INFY", "TCS", ...]

        Must:
        - Never raise — return [] on total failure
        - Return symbols in uppercase, stripped of whitespace
        - Exclude non-equity series (ETFs, bonds, suspended)
        """
        ...

    # ── OHLCV Price Data ─────────────────────────────────────────────

    @abstractmethod
    def fetch_ohlcv(
        self,
        tickers: list[str],
        period: str = "13mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Return a MultiIndex DataFrame with full OHLCV data.

        Column structure: (field, ticker)
        Fields: Open, High, Low, Close, Volume

        Access example:
            df["Close"]["RELIANCE"]   → pd.Series of close prices
            df["Volume"]["INFY"]      → pd.Series of daily volumes

        Args:
            tickers: list of symbols WITHOUT .NS suffix
            period:  yfinance-style period string ("13mo", "1y", etc.)
            interval: candle interval ("1d", "1h")

        Must:
        - Never raise — return empty DataFrame on total failure
        - Skip individual tickers that fail silently
        - Drop tickers with fewer than MIN_DATA_POINTS rows
        """
        ...

    # ── Fundamentals ─────────────────────────────────────────────────

    @abstractmethod
    def fetch_fundamentals(self, tickers: list[str]) -> dict[str, dict]:
        """
        Return fundamental data for each ticker.

        Return structure:
        {
            "RELIANCE": {
                "name":    "Reliance Industries Ltd",
                "sector":  "Energy",
                "ind":     "Oil & Gas Refining",
                "mcap":    1987432.0,   # ₹ Crores
                "pe":      28.4,
                "eps":     95.2,
                "52h":     1608.0,
                "52l":     1116.8,
                "bv":      812.3,
                "dy":      0.37,        # dividend yield %
            },
            ...
        }

        Missing fields should be None, not omitted.
        Never raise — return {} on total failure.
        """
        ...
