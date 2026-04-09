"""
MarketPulse India — Base Scanner (Abstract Interface)

All scanners return the same ScanResult type so the ScoringEngine
can fuse them without knowing which scanner produced them.
"""

from abc import ABC, abstractmethod
import pandas as pd
from engine.opportunity_model import ScanResult


class BaseScanner(ABC):
    """
    Abstract base class for all technical scanners.

    To add a new scanner:
        1. Subclass BaseScanner
        2. Implement scan()
        3. Register in scanners/__init__.py
        4. Add its weight to config/settings.py SCORE_WEIGHTS
    """

    # Override in each scanner — used in signal tags and logging
    NAME: str = "UNKNOWN"
    MAX_SCORE: int = 0

    @abstractmethod
    def scan(self, ohlcv: pd.DataFrame) -> dict[str, ScanResult]:
        """
        Analyse the full OHLCV DataFrame and return per-ticker results.

        Args:
            ohlcv: MultiIndex DataFrame (field × ticker).
                   Fields available: Open, High, Low, Close, Volume.
                   Access: ohlcv["Close"]["RELIANCE"]

        Returns:
            dict mapping ticker str → ScanResult.
            Only include tickers where triggered=True.

        Must never raise. Skip any ticker that fails individually.
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
    def _safe_last(series: pd.Series, default=None):
        """Return last non-NaN value or default."""
        valid = series.dropna()
        return float(valid.iloc[-1]) if len(valid) > 0 else default
