"""
Unit tests for marketpulse/technical/indicators/__init__.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from marketpulse.technical.indicators import (
    adx,
    atr,
    bb_pct_b,
    bb_width,
    bollinger_bands,
    cross_above,
    cross_below,
    ema,
    is_rising,
    macd,
    obv,
    roc,
    rsi,
    sma,
    supertrend,
    trend_slope,
    true_range,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def random_close() -> pd.Series:
    rng = np.random.default_rng(42)
    prices = 100.0 + np.cumsum(rng.normal(0, 1, 300))
    return pd.Series(prices, name="Close")


@pytest.fixture()
def trending_close() -> pd.Series:
    """Steadily rising series — should trigger bullish signals."""
    return pd.Series([100.0 + i * 0.5 for i in range(300)], name="Close")


@pytest.fixture()
def random_hlc(random_close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    rng = np.random.default_rng(99)
    high = random_close + abs(rng.normal(0, 1, len(random_close)))
    low = random_close - abs(rng.normal(0, 1, len(random_close)))
    return high, low, random_close


# ── SMA / EMA ─────────────────────────────────────────────────────────────────


def test_sma_length(random_close: pd.Series) -> None:
    result = sma(random_close, 20)
    assert len(result) == len(random_close)


def test_sma_constant_series() -> None:
    s = pd.Series([5.0] * 50)
    result = sma(s, 10)
    assert (result == 5.0).all()


def test_ema_length(random_close: pd.Series) -> None:
    result = ema(random_close, 20)
    assert len(result) == len(random_close)


def test_ema_faster_than_sma_on_rising(trending_close: pd.Series) -> None:
    """EMA should react faster — its last value should be closer to current price."""
    close = trending_close
    ema_val = float(ema(close, 20).iloc[-1])
    sma_val = float(sma(close, 20).iloc[-1])
    # On a rising series the EMA should be higher than the SMA
    assert ema_val > sma_val


# ── RSI ───────────────────────────────────────────────────────────────────────


def test_rsi_range(random_close: pd.Series) -> None:
    result = rsi(random_close)
    assert result.min() >= 0
    assert result.max() <= 100


def test_rsi_trending_high(trending_close: pd.Series) -> None:
    # Need enough bars for RSI to warm up (14 period ewm)
    # Use a very strong rising series
    strong_up = pd.Series([100.0 + i * 2.0 for i in range(300)])
    result = rsi(strong_up)
    # On a strongly monotonically rising series RSI should be well above 50
    assert float(result.iloc[-1]) > 60


def test_rsi_length(random_close: pd.Series) -> None:
    result = rsi(random_close, 14)
    assert len(result) == len(random_close)


# ── MACD ──────────────────────────────────────────────────────────────────────


def test_macd_returns_three_series(random_close: pd.Series) -> None:
    line, signal, hist = macd(random_close)
    assert len(line) == len(random_close)
    assert len(signal) == len(random_close)
    assert len(hist) == len(random_close)


def test_macd_histogram_equals_line_minus_signal(random_close: pd.Series) -> None:
    line, signal, hist = macd(random_close)
    diff = (line - signal - hist).abs()
    assert diff.max() < 1e-10


def test_macd_trending_bullish(trending_close: pd.Series) -> None:
    line, signal, _hist = macd(trending_close)
    # On rising series MACD line should be above signal
    assert float(line.iloc[-1]) > float(signal.iloc[-1])


# ── Bollinger Bands ───────────────────────────────────────────────────────────


def test_bollinger_upper_above_lower(random_close: pd.Series) -> None:
    upper, _middle, lower = bollinger_bands(random_close)
    assert (upper >= lower).all()


def test_bollinger_middle_is_sma(random_close: pd.Series) -> None:
    _, middle, _ = bollinger_bands(random_close, 20)
    expected = sma(random_close, 20)
    assert (middle - expected).abs().max() < 1e-10


def test_bb_pct_b_between_zero_and_one_mostly(random_close: pd.Series) -> None:
    result = bb_pct_b(random_close)
    # Most values should be between 0 and 1 (within bands)
    within = ((result >= 0) & (result <= 1)).mean()
    assert within > 0.85


def test_bb_width_positive(random_close: pd.Series) -> None:
    result = bb_width(random_close)
    assert (result.dropna() >= 0).all()


# ── ATR ───────────────────────────────────────────────────────────────────────


def test_atr_positive(random_hlc: tuple[pd.Series, pd.Series, pd.Series]) -> None:
    high, low, close = random_hlc
    result = atr(high, low, close)
    assert (result.dropna() > 0).all()


def test_true_range_at_least_hl(random_hlc: tuple[pd.Series, pd.Series, pd.Series]) -> None:
    high, low, close = random_hlc
    tr = true_range(high, low, close)
    hl = high - low
    assert (tr >= hl - 1e-10).all()


# ── ADX ───────────────────────────────────────────────────────────────────────


def test_adx_range(random_hlc: tuple[pd.Series, pd.Series, pd.Series]) -> None:
    high, low, close = random_hlc
    adx_line, _plus_di, _minus_di = adx(high, low, close)
    valid = adx_line.dropna()
    assert (valid >= 0).all()


def test_adx_trending_series(trending_close: pd.Series) -> None:
    rng = np.random.default_rng(7)
    high = trending_close + abs(rng.normal(0, 0.5, len(trending_close)))
    low = trending_close - abs(rng.normal(0, 0.5, len(trending_close)))
    _adx_line, plus_di, minus_di = adx(high, low, trending_close)
    # On a strong trend, +DI should be dominant and ADX should be high
    assert float(plus_di.iloc[-1]) > float(minus_di.iloc[-1])


# ── Supertrend ────────────────────────────────────────────────────────────────


def test_supertrend_direction_values(random_hlc: tuple[pd.Series, pd.Series, pd.Series]) -> None:
    high, low, close = random_hlc
    _, direction = supertrend(high, low, close)
    valid_dirs = direction.dropna().unique()
    assert set(valid_dirs).issubset({1, -1})


def test_supertrend_bullish_on_trending(trending_close: pd.Series) -> None:
    # Use a strong trend with very small noise to guarantee bullish direction
    n = len(trending_close)
    # Prices rise by 2 per bar with tiny noise
    strong = pd.Series([100.0 + i * 2.0 for i in range(n)])
    rng = np.random.default_rng(3)
    noise = abs(rng.normal(0, 0.1, n))
    high = strong + noise
    low = strong - noise
    _, direction = supertrend(high, low, strong, period=7, multiplier=3.0)
    assert int(direction.iloc[-1]) == 1


# ── OBV ───────────────────────────────────────────────────────────────────────


def test_obv_length(random_close: pd.Series) -> None:
    vol = pd.Series([1_000_000.0] * len(random_close))
    result = obv(random_close, vol)
    assert len(result) == len(random_close)


# ── Utility ───────────────────────────────────────────────────────────────────


def test_is_rising_true(trending_close: pd.Series) -> None:
    assert is_rising(trending_close, 5) is True


def test_is_rising_false_on_short_series() -> None:
    assert is_rising(pd.Series([1.0, 2.0, 3.0]), lookback=5) is False


def test_cross_above_detects_crossover() -> None:
    # fast is below slow, then crosses above at index 3
    fast = pd.Series([1.0, 1.0, 1.0, 3.0, 4.0])
    slow = pd.Series([2.0, 2.0, 2.0, 2.0, 2.0])
    result = cross_above(fast, slow)
    # At index 3: fast(3.0) > slow(2.0) AND fast_prev(1.0) <= slow_prev(2.0)
    assert bool(result.iloc[3]) is True


def test_cross_below_detects_crossover() -> None:
    fast = pd.Series([3.0, 3.0, 1.0, 0.5])
    slow = pd.Series([2.0, 2.0, 2.0, 2.0])
    result = cross_below(fast, slow)
    assert result.iloc[2] is True or bool(result.iloc[2])


def test_roc_zero_for_flat() -> None:
    s = pd.Series([5.0] * 50)
    result = roc(s, 10)
    assert result.iloc[-1] == pytest.approx(0.0, abs=1e-10)


def test_trend_slope_positive_for_rising(trending_close: pd.Series) -> None:
    result = trend_slope(trending_close, 5)
    assert float(result.iloc[-1]) > 0
