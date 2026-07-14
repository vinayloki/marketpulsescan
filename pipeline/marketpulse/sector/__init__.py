"""
MarketPulseScan — Sector Rotation & Relative Strength

Ports engine/relative_strength.py with:
  - IBD-style RS Rating (40/20/20/20 weighted returns, percentile ranked)
  - Sector aggregation from universe + snapshots
  - Rotation signals (which sectors are leading/lagging)

Key concepts:
  - RS Rating: 0-100 percentile rank among all stocks
  - Sector RS: median RS Rating of all stocks in the sector
  - Rotation signal: sector trend direction vs. 4-week ago
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import numpy as np
import pandas as pd

from marketpulse.config.sector_map import normalize_sector

if TYPE_CHECKING:
    from collections.abc import Mapping

log = logging.getLogger(__name__)


# ── RS Rating ─────────────────────────────────────────────────────────────────


def rs_rating(
    ohlcv: pd.DataFrame,
    *,
    weights: tuple[float, float, float, float] = (0.40, 0.20, 0.20, 0.20),
    periods: tuple[int, int, int, int] = (63, 126, 189, 252),
) -> pd.Series:
    """
    IBD-style Relative Strength Rating for all stocks in a MultiIndex OHLCV DataFrame.

    Composite weighted return = w1*R3m + w2*R6m + w3*R9m + w4*R12m
    Scores are percentile-ranked 0-100.

    Args:
        ohlcv:   MultiIndex DataFrame (field, symbol).
        weights: Return period weights (default: 40/20/20/20).
        periods: Lookback in trading days for each weight period.

    Returns:
        pd.Series indexed by symbol, values 0-100. NaN for insufficient data.
    """
    if "Close" not in ohlcv.columns.get_level_values(0):
        log.warning("rs_rating: no Close column found")
        return pd.Series(dtype=float)

    close_df = cast("pd.DataFrame", ohlcv["Close"])
    tickers = close_df.columns.tolist()
    min_bars = max(periods)

    rs_raw: dict[str, float] = {}
    for ticker in tickers:
        series = close_df[ticker].dropna()
        if len(series) < min_bars:
            rs_raw[ticker] = np.nan
            continue

        current = float(series.iloc[-1])
        composite = 0.0
        for weight, period in zip(weights, periods, strict=True):
            past = float(series.iloc[-period]) if len(series) >= period else float(series.iloc[0])
            ret = (current - past) / past if past != 0 else 0.0
            composite += weight * ret

        rs_raw[ticker] = composite

    raw_series = pd.Series(rs_raw).dropna()
    if raw_series.empty:
        return raw_series

    rated = raw_series.rank(pct=True) * 100
    log.info("rs_rating: computed RS for %d stocks", len(rated))
    return rated.round(2)


def rs_rating_from_returns(returns: dict[str, float]) -> pd.Series:
    """
    Given a pre-computed {symbol: composite_return} dict,
    return a percentile-ranked pd.Series (0-100).
    Useful when returns are already computed (e.g., from publish bundle).
    """
    if not returns:
        return pd.Series(dtype=float)
    raw = pd.Series(returns).dropna()
    if raw.empty:
        return raw
    return (raw.rank(pct=True) * 100).round(2)


# ── Sector Aggregation ────────────────────────────────────────────────────────


@dataclass
class SectorRank:
    """Aggregated sector-level strength metrics."""

    sector: str
    rs_median: float  # Median RS Rating of all stocks in sector
    rs_mean: float
    stock_count: int
    buy_count: int = 0  # Stocks with recommendation == BUY
    buy_pct: float = 0.0  # % of stocks with BUY
    top_stocks: list[str] = field(default_factory=list)  # Top 3 by RS
    trend: str = "NEUTRAL"  # LEADING | LAGGING | NEUTRAL

    def to_dict(self) -> dict[str, Any]:
        return {
            "sector": self.sector,
            "rs_median": round(self.rs_median, 1),
            "rs_mean": round(self.rs_mean, 1),
            "stock_count": self.stock_count,
            "buy_count": self.buy_count,
            "buy_pct": round(self.buy_pct, 1),
            "top_stocks": self.top_stocks,
            "trend": self.trend,
        }


def sector_ranks(
    rs_scores: pd.Series,
    symbol_sector_map: Mapping[str, str | None],
    recommendations: dict[str, str] | None = None,
    *,
    top_n: int = 3,
) -> list[SectorRank]:
    """
    Aggregate per-stock RS ratings into sector-level rankings.

    Args:
        rs_scores:          pd.Series {symbol → rs_rating (0-100)}.
        symbol_sector_map:  {symbol → sector_name | None}.
        recommendations:    {symbol → "BUY" | "HOLD" | "SELL"} (optional).
        top_n:              Number of top stocks to list per sector.

    Returns:
        List of SectorRank sorted by rs_median descending.
    """
    recs = recommendations or {}

    # Group symbols by normalised sector
    sector_symbols: dict[str, list[str]] = {}
    for sym, raw_sector in symbol_sector_map.items():
        sector = normalize_sector(raw_sector) or "Unknown"
        sector_symbols.setdefault(sector, []).append(sym)

    ranks: list[SectorRank] = []
    for sector, symbols in sector_symbols.items():
        # RS values for stocks that have a rating
        sector_rs = rs_scores.reindex(symbols).dropna()
        if sector_rs.empty:
            continue

        buys = [s for s in symbols if recs.get(s) == "BUY"]
        top = sector_rs.nlargest(top_n).index.tolist()

        rank = SectorRank(
            sector=sector,
            rs_median=float(sector_rs.median()),
            rs_mean=float(sector_rs.mean()),
            stock_count=len(sector_rs),
            buy_count=len(buys),
            buy_pct=len(buys) / len(sector_rs) * 100,
            top_stocks=top,
        )
        ranks.append(rank)

    # Sort by median RS descending
    ranks.sort(key=lambda r: r.rs_median, reverse=True)

    # Classify trend: top third = LEADING, bottom third = LAGGING
    n = len(ranks)
    if n >= 3:
        cutoff_high = n // 3
        cutoff_low = n - n // 3
        for i, r in enumerate(ranks):
            if i < cutoff_high:
                r.trend = "LEADING"
            elif i >= cutoff_low:
                r.trend = "LAGGING"
            else:
                r.trend = "NEUTRAL"

    log.info("sector_ranks: %d sectors ranked", len(ranks))
    return ranks


# ── Rotation Signal ───────────────────────────────────────────────────────────


def rotation_signal(
    current_ranks: list[SectorRank],
    previous_ranks: list[SectorRank],
) -> dict[str, str]:
    """
    Compare current vs previous sector rankings to detect rotation.

    Returns:
        {sector → signal}
        signals: "GAINING" | "LOSING" | "STABLE"
    """
    prev_map = {r.sector: r.rs_median for r in previous_ranks}
    signals: dict[str, str] = {}

    for rank in current_ranks:
        prev_rs = prev_map.get(rank.sector)
        if prev_rs is None:
            signals[rank.sector] = "NEW"
            continue
        diff = rank.rs_median - prev_rs
        if diff > 5:
            signals[rank.sector] = "GAINING"
        elif diff < -5:
            signals[rank.sector] = "LOSING"
        else:
            signals[rank.sector] = "STABLE"

    return signals
