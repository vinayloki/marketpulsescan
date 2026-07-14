"""
Unit tests for marketpulse/scoring/__init__.py
"""

from __future__ import annotations

from marketpulse.scoring import StockScore, rank_opportunities, score_stock
from marketpulse.technical import IndicatorSnapshot

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _bullish_snap(symbol: str = "BULL") -> IndicatorSnapshot:
    """Snapshot with strongly bullish indicator values."""
    return IndicatorSnapshot(
        symbol=symbol,
        close=500.0,
        prev_close=490.0,
        change_pct=2.04,
        high_52w=510.0,
        low_52w=300.0,
        pct_from_52h=-1.96,
        sma20=480.0,
        sma50=450.0,
        sma200=400.0,
        ema9=495.0,
        ema21=490.0,
        ema55=470.0,
        above_sma20=True,
        above_sma50=True,
        above_sma200=True,
        golden_cross=False,
        death_cross=False,
        ma20_slope=0.8,
        ma50_slope=0.5,
        rsi14=62.0,
        rsi_overbought=False,
        rsi_oversold=False,
        macd_line=2.5,
        macd_signal=1.8,
        macd_hist=0.7,
        macd_bullish=True,
        macd_cross_up=False,
        bb_upper=520.0,
        bb_middle=480.0,
        bb_lower=440.0,
        bb_pct_b=0.75,
        bb_squeeze=True,
        atr14=8.0,
        atr_pct=1.6,
        adx14=32.0,
        plus_di=28.0,
        minus_di=12.0,
        trending=True,
        strong_trend=False,
        supertrend_bullish=True,
        obv_rising=True,
    )


def _bearish_snap(symbol: str = "BEAR") -> IndicatorSnapshot:
    """Snapshot with strongly bearish indicator values."""
    return IndicatorSnapshot(
        symbol=symbol,
        close=300.0,
        prev_close=320.0,
        change_pct=-6.25,
        high_52w=600.0,
        low_52w=280.0,
        pct_from_52h=-50.0,
        sma20=350.0,
        sma50=400.0,
        sma200=500.0,
        ema9=305.0,
        ema21=320.0,
        ema55=360.0,
        above_sma20=False,
        above_sma50=False,
        above_sma200=False,
        golden_cross=False,
        death_cross=True,
        ma20_slope=-0.9,
        ma50_slope=-0.4,
        rsi14=28.0,
        rsi_overbought=False,
        rsi_oversold=True,
        macd_line=-5.0,
        macd_signal=-2.0,
        macd_hist=-3.0,
        macd_bullish=False,
        macd_cross_up=False,
        bb_upper=360.0,
        bb_middle=330.0,
        bb_lower=300.0,
        bb_pct_b=0.02,
        bb_squeeze=False,
        atr14=12.0,
        atr_pct=4.0,
        adx14=38.0,
        plus_di=10.0,
        minus_di=30.0,
        trending=True,
        strong_trend=False,
        supertrend_bullish=False,
        obv_rising=False,
    )


# ── StockScore dataclass ──────────────────────────────────────────────────────


def test_stock_score_to_dict() -> None:
    s = StockScore(symbol="TEST", score=75.0, recommendation="BUY")
    d = s.to_dict()
    assert d["symbol"] == "TEST"
    assert d["score"] == 75.0
    assert d["recommendation"] == "BUY"


# ── score_stock ───────────────────────────────────────────────────────────────


def test_score_bullish_snap_is_buy() -> None:
    snap = _bullish_snap()
    result = score_stock(snap)
    assert result.recommendation == "BUY"
    assert result.score >= 65


def test_score_bearish_snap_is_sell_or_hold() -> None:
    snap = _bearish_snap()
    result = score_stock(snap)
    assert result.recommendation in ("SELL", "HOLD")


def test_score_has_all_sub_scores() -> None:
    snap = _bullish_snap()
    result = score_stock(snap)
    assert "momentum" in result.sub_scores
    assert "trend" in result.sub_scores
    assert "breakout" in result.sub_scores
    assert "regime" in result.sub_scores
    assert "mean_reversion" in result.sub_scores


def test_score_sub_scores_in_range() -> None:
    snap = _bullish_snap()
    result = score_stock(snap)
    for name, val in result.sub_scores.items():
        assert 0 <= val <= 100, f"{name}={val} out of range"


def test_score_composite_in_range() -> None:
    for snap in [_bullish_snap(), _bearish_snap()]:
        result = score_stock(snap)
        assert 0 <= result.score <= 100


def test_score_bullish_signals_populated() -> None:
    snap = _bullish_snap()
    result = score_stock(snap)
    assert len(result.signals) > 0


def test_score_includes_fundamental() -> None:
    snap = _bullish_snap()
    fund = {"name": "Bull Corp", "sector": "IT", "mcap_cr": 50000}
    result = score_stock(snap, fund)
    assert result.fundamental.get("name") == "Bull Corp"


def test_score_bullish_has_buy_signals() -> None:
    snap = _bullish_snap()
    result = score_stock(snap)
    # At least one buy-relevant signal
    assert any(
        sig in result.signals
        for sig in (
            "MACD_BULLISH",
            "ABOVE_200MA",
            "SUPERTREND_BULLISH",
            "NEAR_52W_HIGH",
            "BB_SQUEEZE",
        )
    )


def test_score_near_52w_high_signal() -> None:
    snap = _bullish_snap()
    snap.pct_from_52h = -1.0  # within 2% of 52W high
    result = score_stock(snap)
    assert "NEAR_52W_HIGH" in result.signals


def test_score_death_cross_reduces_score() -> None:
    snap_normal = _bullish_snap("A")
    snap_death = _bullish_snap("B")
    snap_death.death_cross = True
    snap_death.golden_cross = False

    r_normal = score_stock(snap_normal)
    r_death = score_stock(snap_death)
    assert r_normal.score > r_death.score


# ── rank_opportunities ────────────────────────────────────────────────────────


def test_rank_opportunities_filters_below_threshold() -> None:
    scores = [
        StockScore(symbol="A", score=80.0, recommendation="BUY"),
        StockScore(symbol="B", score=10.0, recommendation="SELL"),
        StockScore(symbol="C", score=70.0, recommendation="BUY"),
    ]
    result = rank_opportunities(scores, min_score=25, max_results=100)
    symbols = [s.symbol for s in result]
    assert "A" in symbols
    assert "C" in symbols
    assert "B" not in symbols


def test_rank_opportunities_sorted_desc() -> None:
    scores = [
        StockScore(symbol="A", score=60.0, recommendation="HOLD"),
        StockScore(symbol="B", score=90.0, recommendation="BUY"),
        StockScore(symbol="C", score=75.0, recommendation="BUY"),
    ]
    result = rank_opportunities(scores, min_score=0)
    assert result[0].symbol == "B"
    assert result[1].symbol == "C"


def test_rank_opportunities_respects_max() -> None:
    scores = [
        StockScore(symbol=f"S{i}", score=float(80 - i), recommendation="BUY") for i in range(20)
    ]
    result = rank_opportunities(scores, min_score=0, max_results=5)
    assert len(result) == 5


def test_rank_opportunities_empty_input() -> None:
    result = rank_opportunities([], min_score=25)
    assert result == []
