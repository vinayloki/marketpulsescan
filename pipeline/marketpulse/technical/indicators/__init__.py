"""
MarketPulseScan — Technical Indicators

Pure-function library. All functions take a pd.Series (close/high/low/volume)
and return a pd.Series or scalar. No side-effects, no I/O.

Indicators provided:
    Moving averages : sma, ema
    Momentum       : rsi, macd, roc
    Volatility     : bollinger_bands, atr, true_range
    Trend          : adx, supertrend
    Volume         : obv, vwap_approx
    Utility        : trend_slope, is_rising, cross_above, cross_below
"""

from __future__ import annotations

from typing import cast

import numpy as np
import pandas as pd

# ── Moving Averages ───────────────────────────────────────────────────────────


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=1).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average (Wilder-compatible via span)."""
    return series.ewm(span=period, adjust=False, min_periods=1).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average — linearly weighted."""
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(window=period, min_periods=1).apply(
        lambda x: np.dot(x, weights[: len(x)]) / weights[: len(x)].sum(),
        raw=True,
    )


# ── RSI ───────────────────────────────────────────────────────────────────────


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index using Wilder's exponential smoothing.
    Returns values in [0, 100].

    Degenerate cases are handled explicitly so RSI is well-defined even when
    the series moves in only one direction:
      - All gains (no losses)  -> RSI = 100  (e.g. a monotonically rising series)
      - All losses (no gains)  -> RSI = 0
      - Flat (no change)       -> RSI = 50
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    alpha = 1.0 / period
    avg_gain = gain.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi_series = 100.0 - (100.0 / (1.0 + rs))
    rsi_series = rsi_series.replace([np.inf, -np.inf], np.nan)

    # Degenerate one-sided markets NaN out (0/0 or x/0) — pin them to the
    # correct boundary so RSI is always well-defined:
    #   gains but no losses  -> 100  (monotonically rising)
    #   losses but no gains  ->   0  (monotonically falling)
    rsi_series = rsi_series.mask((avg_loss == 0.0) & (avg_gain > 0.0), 100.0)
    rsi_series = rsi_series.mask((avg_gain == 0.0) & (avg_loss > 0.0), 0.0)

    # The first `period` bars are warmup (no smoothing yet) — project a
    # neutral 50 there, leaving all real values untouched.
    return rsi_series.fillna(50.0)


# ── MACD ──────────────────────────────────────────────────────────────────────


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD indicator.

    Returns:
        (macd_line, signal_line, histogram)
        macd_line = EMA(fast) - EMA(slow)
        signal_line = EMA(macd_line, signal)
        histogram = macd_line - signal_line
    """
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    macd_line = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ── Rate of Change ────────────────────────────────────────────────────────────


def roc(series: pd.Series, period: int = 10) -> pd.Series:
    """Rate of Change (percentage)."""
    return series.pct_change(periods=period) * 100.0


# ── Bollinger Bands ───────────────────────────────────────────────────────────


def bollinger_bands(
    series: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands.

    Returns:
        (upper_band, middle_band, lower_band)
        middle = SMA(period)
        upper  = middle + std_dev * rolling_std
        lower  = middle - std_dev * rolling_std
    """
    middle = sma(series, period)
    std = series.rolling(window=period, min_periods=1).std(ddof=0)
    upper = middle + std_dev * std
    lower = middle - std_dev * std
    return upper, middle, lower


def bb_pct_b(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    """
    Bollinger %B — position within the band.
    0 = lower band, 1 = upper band, 0.5 = midline.
    """
    upper, _middle, lower = bollinger_bands(series, period, std_dev)
    width = upper - lower
    return (series - lower) / width.replace(0.0, np.nan)


def bb_width(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> pd.Series:
    """Bollinger Band Width — (upper - lower) / middle."""
    upper, middle, lower = bollinger_bands(series, period, std_dev)
    return (upper - lower) / middle.replace(0.0, np.nan)


# ── ATR / True Range ─────────────────────────────────────────────────────────


def true_range(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
) -> pd.Series:
    """
    True Range: max of (H-L), |H-Cprev|, |L-Cprev|.
    """
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Average True Range (Wilder smoothed)."""
    tr = true_range(high, low, close)
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


# ── ADX ───────────────────────────────────────────────────────────────────────


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Average Directional Index (Wilder smoothed).

    Returns:
        (adx_line, plus_di, minus_di)
        Values in [0, 100]. ADX > 25 = trending.
    """
    alpha = 1.0 / period
    tr = true_range(high, low, close)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    smoothed_tr = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    smoothed_plus = plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    smoothed_minus = minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    plus_di = 100.0 * smoothed_plus / smoothed_tr.replace(0.0, np.nan)
    minus_di = 100.0 * smoothed_minus / smoothed_tr.replace(0.0, np.nan)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    adx_line = dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean()

    return adx_line, plus_di, minus_di


# ── Supertrend ────────────────────────────────────────────────────────────────


def supertrend(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 7,
    multiplier: float = 3.0,
) -> tuple[pd.Series, pd.Series]:
    """
    Supertrend indicator.

    Returns:
        (supertrend_line, direction)
        direction: +1 = uptrend (bullish), -1 = downtrend (bearish)

    Bands are carried forward (only ratchet tighter against the trend) and the
    warmup region where ATR is still NaN is bridged so the indicator does not
    collapse to NaN / a stuck direction on real (noisy) data. Regime is tracked
    with an explicit state variable rather than comparing floats for equality,
    so NaN in the warmup can never flip the direction.
    """
    atr_vals = atr(high, low, close, period)
    # Bridge the ATR warmup (first `period` bars are NaN) so the carry logic has
    # defined bands from bar 0; the early bars are plainly provisional.
    atr_filled = atr_vals.fillna(0.0)
    midpoint = (high + low) / 2.0
    upper_basic = (midpoint + multiplier * atr_filled).to_numpy(dtype=float)
    lower_basic = (midpoint - multiplier * atr_filled).to_numpy(dtype=float)
    closes = close.to_numpy(dtype=float)
    n = len(closes)

    upper = np.copy(upper_basic)
    lower = np.copy(lower_basic)

    # Ratchet the trailing bands: upper only falls, lower only rises — the
    # classic Supertrend carry so support/resistance tighten over time.
    for i in range(1, n):
        if upper_basic[i] < upper[i - 1] or closes[i - 1] > upper[i - 1]:
            upper[i] = upper_basic[i]
        else:
            upper[i] = upper[i - 1]

        if lower_basic[i] > lower[i - 1] or closes[i - 1] < lower[i - 1]:
            lower[i] = lower_basic[i]
        else:
            lower[i] = lower[i - 1]

    direction = np.ones(n, dtype=int)
    st_line = np.full(n, np.nan)
    st_line[0] = lower[0]  # seed bullish

    for i in range(1, n):
        bearish = direction[i - 1] == -1
        if bearish:
            # Latched on the upper band — must break above it to flip bullish.
            direction[i] = 1 if closes[i] > upper[i - 1] else -1
        else:
            # Latched on the lower band — must break below it to flip bearish.
            direction[i] = -1 if closes[i] < lower[i - 1] else 1
        st_line[i] = upper[i] if direction[i] == -1 else lower[i]

    return (
        pd.Series(st_line, index=close.index),
        pd.Series(direction, index=close.index),
    )


# ── Volume Indicators ─────────────────────────────────────────────────────────


def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On-Balance Volume."""
    direction = np.sign(close.diff()).fillna(0)
    return cast("pd.Series", (direction * volume).cumsum())


def vwap_approx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 20,
) -> pd.Series:
    """
    Rolling VWAP approximation (period-day window).
    True VWAP resets daily; this is a useful proxy for swing traders.
    """
    typical_price = (high + low + close) / 3.0
    return (typical_price * volume).rolling(period, min_periods=1).sum() / volume.rolling(
        period, min_periods=1
    ).sum()


# ── Utility ───────────────────────────────────────────────────────────────────


def trend_slope(series: pd.Series, lookback: int = 5) -> pd.Series:
    """Rate-of-change % over `lookback` periods — positive = rising."""
    return series.pct_change(periods=lookback) * 100.0


def is_rising(series: pd.Series, lookback: int = 5) -> bool:
    """True if the last value is above the value `lookback` bars ago."""
    if len(series) <= lookback:
        return False
    return float(series.iloc[-1]) > float(series.iloc[-(lookback + 1)])


def cross_above(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """Boolean Series: True on bars where fast crosses above slow."""
    return (fast > slow) & (fast.shift(1) <= slow.shift(1))


def cross_below(fast: pd.Series, slow: pd.Series) -> pd.Series:
    """Boolean Series: True on bars where fast crosses below slow."""
    return (fast < slow) & (fast.shift(1) >= slow.shift(1))


def price_to_sma_ratio(series: pd.Series, period: int) -> pd.Series:
    """Ratio of price to its SMA. > 1 = above MA, < 1 = below MA."""
    return series / sma(series, period).replace(0.0, np.nan)
