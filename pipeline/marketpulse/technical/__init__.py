"""
MarketPulseScan — Per-Stock Indicator Snapshot

Computes a complete set of technical indicator values for a single stock
from its OHLCV DataFrame. Returns a flat IndicatorSnapshot dataclass
ready to feed into the scoring engine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from marketpulse.technical.indicators import (
    adx,
    atr,
    bb_pct_b,
    bollinger_bands,
    cross_above,
    cross_below,
    ema,
    is_rising,
    macd,
    obv,
    rsi,
    sma,
    supertrend,
    trend_slope,
)

log = logging.getLogger(__name__)

# Standard MA periods (swing-trading defaults)
SMA_PERIODS = (20, 50, 200)
EMA_PERIODS = (9, 21, 55)


@dataclass
class IndicatorSnapshot:
    """
    All indicator values for one stock at the latest bar.

    Scalar fields hold the *current* value (last bar).
    Boolean fields indicate whether a condition is true right now.
    """

    symbol: str

    # Price / returns
    close: float | None = None
    prev_close: float | None = None
    change_pct: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None
    pct_from_52h: float | None = None  # % below 52-week high (negative = below)

    # Moving averages (value / above-MA flag)
    sma20: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    ema9: float | None = None
    ema21: float | None = None
    ema55: float | None = None
    above_sma20: bool = False
    above_sma50: bool = False
    above_sma200: bool = False
    golden_cross: bool = False  # SMA50 > SMA200 and just crossed
    death_cross: bool = False

    # RSI
    rsi14: float | None = None
    rsi_overbought: bool = False  # > 70
    rsi_oversold: bool = False  # < 30
    rsi_mid_cross_up: bool = False  # RSI crossed above 50

    # MACD
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_hist: float | None = None
    macd_bullish: bool = False  # hist > 0 and line > signal
    macd_cross_up: bool = False  # MACD crossed above signal this bar

    # Bollinger Bands
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_pct_b: float | None = None  # position 0-1 within band
    bb_squeeze: bool = False  # width < 20th percentile of last 6mo

    # ATR / Volatility
    atr14: float | None = None
    atr_pct: float | None = None  # ATR as % of price

    # ADX / Trend strength
    adx14: float | None = None
    plus_di: float | None = None
    minus_di: float | None = None
    trending: bool = False  # ADX > 25
    strong_trend: bool = False  # ADX > 40

    # Supertrend
    supertrend_bullish: bool = False  # direction == +1

    # Volume
    obv_rising: bool = False

    # Trend slope
    ma20_slope: float | None = None  # % change of SMA20 over 5 bars
    ma50_slope: float | None = None

    # Raw signals list (populated by scanner)
    signals: list[str] = field(default_factory=list)

    # Arbitrary extra computed values for downstream use
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Flat dict for JSON serialisation (excludes None values)."""
        return {
            k: v
            for k, v in self.__dict__.items()
            if v is not None and k not in ("signals", "extra")
        }


def compute_snapshot(
    symbol: str,
    ohlcv: pd.DataFrame,
    *,
    min_bars: int = 60,
) -> IndicatorSnapshot | None:
    """
    Compute a full IndicatorSnapshot for `symbol` from a MultiIndex OHLCV DataFrame.

    Args:
        symbol:   NSE ticker (no .NS suffix).
        ohlcv:    MultiIndex DataFrame with columns (field, symbol).
        min_bars: Minimum rows of valid data required (default: 60).

    Returns:
        IndicatorSnapshot or None if data is insufficient.
    """
    snap = IndicatorSnapshot(symbol=symbol)

    # ── Extract OHLCV series ──────────────────────────────────────────
    try:
        if isinstance(ohlcv.columns, pd.MultiIndex):
            sym_key = symbol if symbol in ohlcv.columns.get_level_values(1) else f"{symbol}.NS"
            close = ohlcv["Close"][sym_key].dropna()
            high = ohlcv["High"][sym_key].dropna()
            low = ohlcv["Low"][sym_key].dropna()
            vol = (
                ohlcv["Volume"][sym_key].dropna()
                if "Volume" in ohlcv.columns.get_level_values(0)
                else pd.Series(dtype=float)
            )
        else:
            close = ohlcv["Close"].dropna() if "Close" in ohlcv.columns else pd.Series(dtype=float)
            high = ohlcv["High"].dropna() if "High" in ohlcv.columns else pd.Series(dtype=float)
            low = ohlcv["Low"].dropna() if "Low" in ohlcv.columns else pd.Series(dtype=float)
            vol = ohlcv["Volume"].dropna() if "Volume" in ohlcv.columns else pd.Series(dtype=float)
    except (KeyError, TypeError):
        log.debug("compute_snapshot: data extraction failed for %s", symbol)
        return None

    if len(close) < min_bars:
        log.debug("compute_snapshot: insufficient data for %s (%d bars)", symbol, len(close))
        return None

    # Align all series to close index
    high = high.reindex(close.index).ffill()
    low = low.reindex(close.index).ffill()
    vol = vol.reindex(close.index).fillna(0)

    # ── Price basics ──────────────────────────────────────────────────
    snap.close = round(float(close.iloc[-1]), 2)
    if len(close) >= 2:
        snap.prev_close = round(float(close.iloc[-2]), 2)
        snap.change_pct = round((snap.close - snap.prev_close) / snap.prev_close * 100, 2)

    year_slice = close.iloc[-252:] if len(close) >= 252 else close
    snap.high_52w = round(float(year_slice.max()), 2)
    snap.low_52w = round(float(year_slice.min()), 2)
    if snap.high_52w:
        snap.pct_from_52h = round((snap.close - snap.high_52w) / snap.high_52w * 100, 2)

    # ── Moving averages ───────────────────────────────────────────────
    sma20_s = sma(close, 20)
    sma50_s = sma(close, 50)
    sma200_s = sma(close, 200)
    ema9_s = ema(close, 9)
    ema21_s = ema(close, 21)
    ema55_s = ema(close, 55)

    snap.sma20 = round(float(sma20_s.iloc[-1]), 2)
    snap.sma50 = round(float(sma50_s.iloc[-1]), 2)
    snap.sma200 = round(float(sma200_s.iloc[-1]), 2)
    snap.ema9 = round(float(ema9_s.iloc[-1]), 2)
    snap.ema21 = round(float(ema21_s.iloc[-1]), 2)
    snap.ema55 = round(float(ema55_s.iloc[-1]), 2)

    snap.above_sma20 = snap.close > snap.sma20
    snap.above_sma50 = snap.close > snap.sma50
    snap.above_sma200 = snap.close > snap.sma200

    snap.golden_cross = bool(cross_above(sma50_s, sma200_s).iloc[-1])
    snap.death_cross = bool(cross_below(sma50_s, sma200_s).iloc[-1])

    snap.ma20_slope = round(float(trend_slope(sma20_s, 5).iloc[-1]), 3)
    snap.ma50_slope = round(float(trend_slope(sma50_s, 5).iloc[-1]), 3)

    # ── RSI ───────────────────────────────────────────────────────────
    rsi_s = rsi(close, 14)
    snap.rsi14 = round(float(rsi_s.iloc[-1]), 2)
    snap.rsi_overbought = snap.rsi14 > 70
    snap.rsi_oversold = snap.rsi14 < 30
    snap.rsi_mid_cross_up = bool(cross_above(rsi_s, pd.Series(50.0, index=rsi_s.index)).iloc[-1])

    # ── MACD ──────────────────────────────────────────────────────────
    macd_l, macd_sig, macd_h = macd(close)
    snap.macd_line = round(float(macd_l.iloc[-1]), 4)
    snap.macd_signal = round(float(macd_sig.iloc[-1]), 4)
    snap.macd_hist = round(float(macd_h.iloc[-1]), 4)
    snap.macd_bullish = snap.macd_line > snap.macd_signal and snap.macd_hist > 0
    snap.macd_cross_up = bool(cross_above(macd_l, macd_sig).iloc[-1])

    # ── Bollinger Bands ───────────────────────────────────────────────
    bb_u, bb_m, bb_l = bollinger_bands(close)
    snap.bb_upper = round(float(bb_u.iloc[-1]), 2)
    snap.bb_middle = round(float(bb_m.iloc[-1]), 2)
    snap.bb_lower = round(float(bb_l.iloc[-1]), 2)
    pct_b_s = bb_pct_b(close)
    snap.bb_pct_b = round(float(pct_b_s.iloc[-1]), 4)

    # Squeeze: current width in the bottom 20th percentile of last 126 bars
    from marketpulse.technical.indicators import bb_width

    bw = bb_width(close)
    bw_window = bw.iloc[-126:] if len(bw) >= 126 else bw
    snap.bb_squeeze = float(bw.iloc[-1]) < float(bw_window.quantile(0.20))

    # ── ATR ───────────────────────────────────────────────────────────
    atr_s = atr(high, low, close, 14)
    snap.atr14 = round(float(atr_s.iloc[-1]), 2)
    snap.atr_pct = round(snap.atr14 / snap.close * 100, 2) if snap.close else None

    # ── ADX ───────────────────────────────────────────────────────────
    adx_s, plus_di_s, minus_di_s = adx(high, low, close, 14)
    snap.adx14 = round(float(adx_s.iloc[-1]), 2)
    snap.plus_di = round(float(plus_di_s.iloc[-1]), 2)
    snap.minus_di = round(float(minus_di_s.iloc[-1]), 2)
    snap.trending = snap.adx14 > 25
    snap.strong_trend = snap.adx14 > 40

    # ── Supertrend ────────────────────────────────────────────────────
    _, st_dir = supertrend(high, low, close)
    snap.supertrend_bullish = int(st_dir.iloc[-1]) == 1

    # ── OBV ───────────────────────────────────────────────────────────
    if not vol.empty and vol.sum() > 0:
        obv_s = obv(close, vol)
        snap.obv_rising = is_rising(obv_s, 5)

    return snap
