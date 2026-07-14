"""
Unit tests for marketpulse/technical/__init__.py (IndicatorSnapshot + compute_snapshot)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from marketpulse.technical import IndicatorSnapshot, compute_snapshot

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_multiindex_ohlcv(symbol: str = "TEST", n: int = 300) -> pd.DataFrame:
    """Build a synthetic MultiIndex OHLCV DataFrame."""
    rng = np.random.default_rng(42)
    prices = 100.0 + np.cumsum(rng.normal(0, 1, n))
    idx = pd.date_range("2023-01-01", periods=n, freq="B")

    close = pd.Series(prices, index=idx)
    high = close + abs(rng.normal(0, 1, n))
    low = close - abs(rng.normal(0, 1, n))
    volume = pd.Series(rng.integers(100_000, 5_000_000, n).astype(float), index=idx)
    open_ = close.shift(1).fillna(close)

    cols = pd.MultiIndex.from_arrays([["Open", "High", "Low", "Close", "Volume"], [symbol] * 5])
    df = pd.concat([open_, high, low, close, volume], axis=1)
    df.columns = cols
    return df


def _make_trending_ohlcv(symbol: str = "TREND", n: int = 300) -> pd.DataFrame:
    """Monotonically rising price — should yield bullish snapshot."""
    idx = pd.date_range("2023-01-01", periods=n, freq="B")
    prices = pd.Series([100.0 + i * 0.5 for i in range(n)], index=idx)
    rng = np.random.default_rng(7)
    high = prices + abs(rng.normal(0, 0.3, n))
    low = prices - abs(rng.normal(0, 0.3, n))
    volume = pd.Series([1_000_000.0] * n, index=idx)
    open_ = prices.shift(1).fillna(prices)

    cols = pd.MultiIndex.from_arrays([["Open", "High", "Low", "Close", "Volume"], [symbol] * 5])
    df = pd.concat([open_, high, low, prices, volume], axis=1)
    df.columns = cols
    return df


# ── IndicatorSnapshot dataclass ───────────────────────────────────────────────


def test_snapshot_defaults() -> None:
    snap = IndicatorSnapshot(symbol="TEST")
    assert snap.symbol == "TEST"
    assert snap.close is None
    assert snap.rsi14 is None
    assert snap.signals == []


def test_snapshot_to_dict_excludes_none() -> None:
    snap = IndicatorSnapshot(symbol="TEST", close=150.0, rsi14=55.0)
    d = snap.to_dict()
    assert "close" in d
    assert "rsi14" in d
    # Fields that are None should be excluded
    assert "macd_line" not in d


# ── compute_snapshot ──────────────────────────────────────────────────────────


def test_compute_snapshot_returns_snapshot() -> None:
    ohlcv = _make_multiindex_ohlcv("RELIANCE")
    snap = compute_snapshot("RELIANCE", ohlcv)
    assert snap is not None
    assert snap.symbol == "RELIANCE"


def test_compute_snapshot_returns_none_for_insufficient_data() -> None:
    ohlcv = _make_multiindex_ohlcv("X", n=30)
    snap = compute_snapshot("X", ohlcv, min_bars=60)
    assert snap is None


def test_compute_snapshot_returns_none_for_missing_symbol() -> None:
    ohlcv = _make_multiindex_ohlcv("RELIANCE")
    snap = compute_snapshot("UNKNOWN", ohlcv)
    assert snap is None


def test_compute_snapshot_price_fields() -> None:
    ohlcv = _make_multiindex_ohlcv("TCS")
    snap = compute_snapshot("TCS", ohlcv)
    assert snap is not None
    assert snap.close is not None and snap.close > 0
    assert snap.high_52w is not None
    assert snap.low_52w is not None
    assert snap.high_52w >= snap.close or snap.high_52w >= snap.low_52w


def test_compute_snapshot_rsi_in_range() -> None:
    ohlcv = _make_multiindex_ohlcv("INFY")
    snap = compute_snapshot("INFY", ohlcv)
    assert snap is not None
    assert snap.rsi14 is not None
    assert 0 <= snap.rsi14 <= 100


def test_compute_snapshot_ma_fields_populated() -> None:
    ohlcv = _make_multiindex_ohlcv("HDFCBANK")
    snap = compute_snapshot("HDFCBANK", ohlcv)
    assert snap is not None
    assert snap.sma20 is not None
    assert snap.sma50 is not None
    assert snap.sma200 is not None
    assert snap.ema9 is not None


def test_compute_snapshot_macd_populated() -> None:
    ohlcv = _make_multiindex_ohlcv("TATAMOTORS")
    snap = compute_snapshot("TATAMOTORS", ohlcv)
    assert snap is not None
    assert snap.macd_line is not None
    assert snap.macd_signal is not None
    assert snap.macd_hist is not None


def test_compute_snapshot_atr_positive() -> None:
    ohlcv = _make_multiindex_ohlcv("AXISBANK")
    snap = compute_snapshot("AXISBANK", ohlcv)
    assert snap is not None
    assert snap.atr14 is not None and snap.atr14 > 0
    assert snap.atr_pct is not None and snap.atr_pct > 0


def test_compute_snapshot_adx_populated() -> None:
    ohlcv = _make_multiindex_ohlcv("WIPRO")
    snap = compute_snapshot("WIPRO", ohlcv)
    assert snap is not None
    assert snap.adx14 is not None and snap.adx14 >= 0


def test_compute_snapshot_bollinger_order() -> None:
    ohlcv = _make_multiindex_ohlcv("ITC")
    snap = compute_snapshot("ITC", ohlcv)
    assert snap is not None
    assert snap.bb_upper is not None
    assert snap.bb_lower is not None
    assert snap.bb_upper >= snap.bb_lower


def test_compute_snapshot_trending_is_bullish() -> None:
    ohlcv = _make_trending_ohlcv("BULL")
    snap = compute_snapshot("BULL", ohlcv)
    assert snap is not None
    assert snap.above_sma20 is True
    assert snap.above_sma50 is True
    # RSI should be bullish on a rising series
    assert snap.rsi14 is not None and snap.rsi14 > 50


def test_compute_snapshot_obv_flag() -> None:
    ohlcv = _make_trending_ohlcv("VOLUP")
    snap = compute_snapshot("VOLUP", ohlcv)
    assert snap is not None
    # OBV should be rising on a consistently rising price with constant volume
    assert snap.obv_rising is True
