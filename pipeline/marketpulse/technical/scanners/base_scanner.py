"""
MarketPulse — Base Scanner (Abstract Interface)

All scanners return the same ScanResult type so downstream scoring or DB
persistence can process them uniformly.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class ScanResult:
    """Output of one scanner for one ticker."""

    ticker: str
    scanner: str  # scanner name e.g. "52W_BREAKOUT"
    triggered: bool = False
    score: int = 0  # 0-max_score for this scanner
    signals: list[str] = field(default_factory=list)
    indicators: dict[str, Any] = field(default_factory=dict)


class BaseScanner(ABC):
    """
    Abstract base class for all technical scanners.
    """

    # Override in each scanner — used in signal tags and logging
    NAME: str = "UNKNOWN"
    MAX_SCORE: int = 0

    @abstractmethod
    def scan(self, ohlcv: pd.DataFrame) -> dict[str, ScanResult]:
        """
        Analyse the full OHLCV DataFrame and return per-ticker results.

        Args:
            ohlcv: MultiIndex DataFrame (field x ticker).
                   Fields available: Open, High, Low, Close, Volume.
                   Access: ohlcv["Close"]["RELIANCE"]

        Returns:
            dict mapping ticker str → ScanResult.
            Only include tickers where triggered=True.
        """
        ...

    # ── Shared helpers (available to all subclasses) ──────────────────

    @staticmethod
    def _ema(series: pd.Series, span: int) -> pd.Series:
        """Exponential moving average (Wilder-style adjust=False)."""
        return series.ewm(span=span, adjust=False).mean()

    @staticmethod
    def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
        """
        RSI using Wilder's smoothing (ewm com = period-1).
        Same formula as TradingView's default RSI.
        """
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _vol_sma(volume: pd.Series, window: int = 20) -> pd.Series:
        """Simple moving average of volume."""
        return volume.rolling(window=window, min_periods=window).mean()

    @staticmethod
    def _safe_last(series: pd.Series, default: float | None = None) -> float | None:
        """Return last non-NaN value or default."""
        valid = series.dropna()
        return float(valid.iloc[-1]) if len(valid) > 0 else default
