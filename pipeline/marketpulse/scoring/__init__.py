"""
MarketPulseScan — Scoring Engine

Fuses technical indicator snapshots into a 0-100 composite score
with a BUY / HOLD / SELL recommendation.

Scoring model (preserved from legacy scoring_engine.py + ai_engine.py):
    30%  Momentum score   — RSI, MACD, ROC
    25%  Trend score      — MA alignment, ADX, Supertrend
    20%  Breakout score   — 52W proximity, Bollinger squeeze, volume
    15%  Regime score     — market trend context (ATR normalised)
    10%  Mean-reversion   — RSI extremes, %B position

Multi-signal bonus (preserved from legacy):
    2 signal types → +5 pts
    3 signal types → +10 pts

Thresholds:
    Score >= 65 → BUY
    Score >= 40 → HOLD
    Score < 40  → SELL
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from marketpulse.config.sector_map import normalize_sector
from marketpulse.config.settings import (
    MAX_OPPORTUNITIES,
    MIN_SCORE_THRESHOLD,
    MULTI_SIGNAL_BONUS,
)

if TYPE_CHECKING:
    from marketpulse.technical import IndicatorSnapshot

log = logging.getLogger(__name__)

# Score component weights (must sum to 1.0)
_WEIGHTS = {
    "momentum": 0.30,
    "trend": 0.25,
    "breakout": 0.20,
    "regime": 0.15,
    "mean_reversion": 0.10,
}

# Recommendation thresholds
_BUY_THRESHOLD = 65
_HOLD_THRESHOLD = 40


@dataclass
class StockScore:
    """Final scored output for one stock."""

    symbol: str
    score: float  # 0-100
    recommendation: str  # BUY | HOLD | SELL
    signals: list[str] = field(default_factory=list)
    sub_scores: dict[str, float] = field(default_factory=dict)
    indicators: dict[str, Any] = field(default_factory=dict)
    fundamental: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "score": round(self.score, 1),
            "recommendation": self.recommendation,
            "signals": self.signals,
            "sub_scores": {k: round(v, 1) for k, v in self.sub_scores.items()},
            "indicators": self.indicators,
            "fundamental": self.fundamental,
        }


# ── Component scorers ─────────────────────────────────────────────────────────


def _momentum_score(snap: IndicatorSnapshot) -> tuple[float, list[str]]:
    """
    Momentum sub-score (0-100) from RSI, MACD, and rate-of-change signals.
    """
    score = 50.0
    signals: list[str] = []

    if snap.rsi14 is not None:
        rsi = snap.rsi14
        if 50 < rsi <= 65:
            score += 15
            signals.append("RSI_BULLISH_ZONE")
        elif rsi > 65:
            score += 8  # overbought — reduced weight
        elif rsi < 30:
            score -= 20
            signals.append("RSI_OVERSOLD")
        elif rsi < 45:
            score -= 10

    if snap.macd_bullish:
        score += 15
        signals.append("MACD_BULLISH")
    elif snap.macd_hist is not None and snap.macd_hist < 0:
        score -= 10

    if snap.macd_cross_up:
        score += 10
        signals.append("MACD_CROSS_UP")

    if snap.rsi_mid_cross_up:
        score += 8
        signals.append("RSI_MID_CROSS")

    return max(0.0, min(100.0, score)), signals


def _trend_score(snap: IndicatorSnapshot) -> tuple[float, list[str]]:
    """
    Trend sub-score (0-100) from MA alignment, ADX, Supertrend.
    """
    score = 40.0
    signals: list[str] = []

    # MA alignment — above key MAs
    ma_count = sum([snap.above_sma20, snap.above_sma50, snap.above_sma200])
    score += ma_count * 10

    if snap.above_sma200:
        signals.append("ABOVE_200MA")
    if snap.above_sma50 and snap.above_sma200:
        signals.append("ABOVE_50_200MA")

    # Golden/death cross
    if snap.golden_cross:
        score += 12
        signals.append("GOLDEN_CROSS")
    elif snap.death_cross:
        score -= 15

    # ADX trend strength
    if snap.adx14 is not None:
        if snap.strong_trend and snap.plus_di is not None and snap.minus_di is not None:
            if snap.plus_di > snap.minus_di:
                score += 15
                signals.append("STRONG_UPTREND")
        elif (
            snap.trending
            and snap.plus_di is not None
            and snap.minus_di is not None
            and snap.plus_di > snap.minus_di
        ):
            score += 8

    # Supertrend
    if snap.supertrend_bullish:
        score += 10
        signals.append("SUPERTREND_BULLISH")
    else:
        score -= 8

    # MA slopes
    if snap.ma20_slope is not None and snap.ma20_slope > 0:
        score += 5
    if snap.ma50_slope is not None and snap.ma50_slope > 0:
        score += 3

    return max(0.0, min(100.0, score)), signals


def _breakout_score(snap: IndicatorSnapshot) -> tuple[float, list[str]]:
    """
    Breakout sub-score (0-100) from 52W proximity, Bollinger squeeze, OBV.
    """
    score = 40.0
    signals: list[str] = []

    # 52-week high proximity
    if snap.pct_from_52h is not None:
        pct = snap.pct_from_52h  # negative = below 52H
        if pct >= -2:  # within 2% of 52W high
            score += 25
            signals.append("NEAR_52W_HIGH")
        elif pct >= -10:
            score += 12
        elif pct < -30:
            score -= 10

    # Bollinger squeeze — coiling before breakout
    if snap.bb_squeeze:
        score += 12
        signals.append("BB_SQUEEZE")

    # Price position within Bollinger band
    if snap.bb_pct_b is not None:
        pct_b = snap.bb_pct_b
        if pct_b > 0.8:  # upper band — strong momentum
            score += 8
        elif pct_b < 0.2:  # lower band — potential mean reversion
            score -= 5

    # OBV rising confirms breakout
    if snap.obv_rising:
        score += 10
        signals.append("OBV_RISING")

    return max(0.0, min(100.0, score)), signals


def _regime_score(snap: IndicatorSnapshot) -> tuple[float, list[str]]:
    """
    Regime sub-score (0-100) — volatility-normalised trend context.
    Uses ATR % as a proxy for regime.
    """
    score = 50.0
    signals: list[str] = []

    if snap.atr_pct is not None:
        atr_pct = snap.atr_pct
        if atr_pct < 1.5:  # low volatility — stable regime
            score += 20
            if snap.above_sma200:
                signals.append("LOW_VOL_UPTREND")
        elif atr_pct < 3.0:
            score += 5
        elif atr_pct > 5.0:  # high volatility — risky regime
            score -= 15

    # Broad trend: price above 200 MA = bull regime
    if snap.above_sma200:
        score += 15
    else:
        score -= 10

    return max(0.0, min(100.0, score)), signals


def _mean_reversion_score(snap: IndicatorSnapshot) -> tuple[float, list[str]]:
    """
    Mean-reversion sub-score (0-100) — opportunity in pullbacks.
    """
    score = 50.0
    signals: list[str] = []

    if snap.rsi_oversold:
        score += 30
        signals.append("RSI_OVERSOLD_BOUNCE")
    elif snap.rsi14 is not None and snap.rsi14 < 40:
        score += 15

    if snap.bb_pct_b is not None and snap.bb_pct_b < 0.15:
        score += 20
        signals.append("BB_LOWER_TOUCH")

    # Only valid if price is above 200 MA (confirms it's a pullback, not a breakdown)
    if not snap.above_sma200:
        score -= 20

    return max(0.0, min(100.0, score)), signals


# ── Main scorer ───────────────────────────────────────────────────────────────


def score_stock(
    snap: IndicatorSnapshot,
    fundamental: dict[str, Any] | None = None,
) -> StockScore:
    """
    Compute composite score for a single stock from its IndicatorSnapshot.

    Args:
        snap:        Pre-computed IndicatorSnapshot.
        fundamental: Optional fundamental dict (from YFinanceProvider).

    Returns:
        StockScore with composite score, recommendation, and sub-scores.
    """
    fund = fundamental or {}

    # ── Component scores ──────────────────────────────────────────────
    mom_score, mom_sigs = _momentum_score(snap)
    trend_score, trend_sigs = _trend_score(snap)
    bo_score, bo_sigs = _breakout_score(snap)
    reg_score, reg_sigs = _regime_score(snap)
    mr_score, mr_sigs = _mean_reversion_score(snap)

    sub_scores = {
        "momentum": mom_score,
        "trend": trend_score,
        "breakout": bo_score,
        "regime": reg_score,
        "mean_reversion": mr_score,
    }

    # ── Composite (weighted average) ──────────────────────────────────
    composite = sum(_WEIGHTS[k] * sub_scores[k] for k in _WEIGHTS)

    # ── Multi-signal bonus ────────────────────────────────────────────
    all_signals = mom_sigs + trend_sigs + bo_sigs + reg_sigs + mr_sigs
    n_signal_types = len({s.split("_")[0] for s in all_signals})
    bonus = MULTI_SIGNAL_BONUS.get(n_signal_types, 0)
    composite = min(100.0, composite + bonus)

    # ── Recommendation ────────────────────────────────────────────────
    if composite >= _BUY_THRESHOLD:
        recommendation = "BUY"
    elif composite >= _HOLD_THRESHOLD:
        recommendation = "HOLD"
    else:
        recommendation = "SELL"

    return StockScore(
        symbol=snap.symbol,
        score=composite,
        recommendation=recommendation,
        signals=sorted(set(all_signals)),
        sub_scores=sub_scores,
        indicators=snap.to_dict(),
        fundamental={
            "name": fund.get("name"),
            "sector": normalize_sector(fund.get("sector")),
            "industry": fund.get("industry"),
            "mcap_cr": fund.get("mcap_cr"),
            "pe": fund.get("pe"),
            "roe": fund.get("roe"),
            "52h": snap.high_52w,
            "52l": snap.low_52w,
        },
    )


def rank_opportunities(
    scores: list[StockScore],
    *,
    min_score: float = MIN_SCORE_THRESHOLD,
    max_results: int = MAX_OPPORTUNITIES,
) -> list[StockScore]:
    """
    Filter to stocks above min_score, sort by score descending, cap at max_results.
    """
    qualified = [s for s in scores if s.score >= min_score]
    ranked = sorted(qualified, key=lambda x: x.score, reverse=True)
    return ranked[:max_results]
