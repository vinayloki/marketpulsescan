"""
Unit tests for marketpulse/sector/__init__.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from marketpulse.sector import (
    SectorRank,
    rotation_signal,
    rs_rating,
    rs_rating_from_returns,
    sector_ranks,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_multiindex_ohlcv(n_stocks: int = 5, n_bars: int = 260) -> pd.DataFrame:
    """Synthetic MultiIndex OHLCV with n_stocks tickers."""
    rng = np.random.default_rng(42)
    symbols = [f"SYM{i}" for i in range(n_stocks)]
    idx = pd.date_range("2023-01-01", periods=n_bars, freq="B")

    frames = {}
    for sym in symbols:
        prices = 100.0 + np.cumsum(rng.normal(0, 1, n_bars))
        frames[sym] = pd.Series(prices, index=idx)

    close_df = pd.DataFrame(frames)
    arrays = [["Close"] * n_stocks, symbols]
    close_df.columns = pd.MultiIndex.from_arrays(arrays)
    return close_df


# ── rs_rating ─────────────────────────────────────────────────────────────────


def test_rs_rating_returns_series() -> None:
    ohlcv = _make_multiindex_ohlcv(5, 260)
    result = rs_rating(ohlcv)
    assert isinstance(result, pd.Series)
    assert len(result) == 5


def test_rs_rating_values_0_to_100() -> None:
    ohlcv = _make_multiindex_ohlcv(10, 260)
    result = rs_rating(ohlcv)
    assert result.min() >= 0
    assert result.max() <= 100


def test_rs_rating_percentile_has_50th() -> None:
    ohlcv = _make_multiindex_ohlcv(10, 260)
    result = rs_rating(ohlcv)
    # With 10 stocks, one should be near 50 (median)
    assert abs(result.median() - 50) < 15


def test_rs_rating_empty_df() -> None:
    empty = pd.DataFrame(columns=pd.MultiIndex.from_tuples([("Close", "X")]))
    result = rs_rating(empty)
    assert result.empty


def test_rs_rating_insufficient_bars_returns_nan() -> None:
    ohlcv = _make_multiindex_ohlcv(3, 100)  # < 252 bars required
    result = rs_rating(ohlcv)
    # Should return NaN for all stocks (insufficient history)
    assert result.isna().all()


def test_rs_rating_winner_has_high_score() -> None:
    """The stock with the highest cumulative return should rank highest."""
    n = 260
    idx = pd.date_range("2022-01-01", periods=n, freq="B")
    # SYM0 has strong upward trend, SYM1 is flat
    sym0 = pd.Series(100.0 + np.arange(n) * 0.5, index=idx)  # strong winner
    sym1 = pd.Series([100.0] * n, index=idx)  # flat loser

    cols = pd.MultiIndex.from_arrays([["Close", "Close"], ["SYM0", "SYM1"]])
    df = pd.concat([sym0, sym1], axis=1)
    df.columns = cols

    result = rs_rating(df)
    assert result["SYM0"] > result["SYM1"]


# ── rs_rating_from_returns ────────────────────────────────────────────────────


def test_rs_rating_from_returns_returns_series() -> None:
    returns = {"A": 0.30, "B": 0.10, "C": -0.05}
    result = rs_rating_from_returns(returns)
    assert isinstance(result, pd.Series)
    assert len(result) == 3


def test_rs_rating_from_returns_highest_is_100() -> None:
    returns = {"A": 0.50, "B": 0.10, "C": -0.20}
    result = rs_rating_from_returns(returns)
    assert result["A"] == pytest.approx(100.0, rel=0.01)


def test_rs_rating_from_returns_empty() -> None:
    result = rs_rating_from_returns({})
    assert result.empty


# ── sector_ranks ──────────────────────────────────────────────────────────────


def test_sector_ranks_returns_list() -> None:
    rs = pd.Series({"A": 80.0, "B": 60.0, "C": 40.0, "D": 20.0})
    sym_sector = {"A": "IT", "B": "IT", "C": "Banks", "D": "Banks"}
    result = sector_ranks(rs, sym_sector)
    assert isinstance(result, list)
    assert len(result) == 2


def test_sector_ranks_sorted_by_rs_median() -> None:
    rs = pd.Series({"A": 90.0, "B": 80.0, "C": 30.0, "D": 20.0})
    sym_sector = {"A": "IT", "B": "IT", "C": "Banking", "D": "Banking"}
    result = sector_ranks(rs, sym_sector)
    # sector_ranks normalizes raw names to canonical sector labels
    assert result[0].sector == "IT & Technology"
    assert result[1].sector == "Banking & Finance"


def test_sector_ranks_has_correct_stock_count() -> None:
    rs = pd.Series({"A": 90.0, "B": 80.0, "C": 70.0, "D": 20.0})
    sym_sector = {"A": "IT", "B": "IT", "C": "IT", "D": "Banking"}
    result = sector_ranks(rs, sym_sector)
    it_rank = next(r for r in result if r.sector == "IT & Technology")
    assert it_rank.stock_count == 3


def test_sector_ranks_buy_count() -> None:
    rs = pd.Series({"A": 90.0, "B": 80.0, "C": 30.0})
    sym_sector = {"A": "IT", "B": "IT", "C": "IT"}
    recs = {"A": "BUY", "B": "BUY", "C": "SELL"}
    result = sector_ranks(rs, sym_sector, recs)
    assert result[0].buy_count == 2
    assert result[0].buy_pct == pytest.approx(66.67, rel=0.01)


def test_sector_ranks_leading_lagging() -> None:
    rs = pd.Series({f"S{i}": float(100 - i * 10) for i in range(9)})
    sectors = {f"S{i}": ["IT", "Banks", "Pharma"][i % 3] for i in range(9)}
    result = sector_ranks(rs, sectors)
    trends = {r.sector: r.trend for r in result}
    assert "LEADING" in trends.values()
    assert "LAGGING" in trends.values()


def test_sector_ranks_empty_rs() -> None:
    rs = pd.Series(dtype=float)
    sym_sector = {"A": "IT", "B": "Banks"}
    result = sector_ranks(rs, sym_sector)
    assert result == []


def test_sector_ranks_top_stocks_limited() -> None:
    rs = pd.Series({"A": 90.0, "B": 80.0, "C": 70.0, "D": 60.0, "E": 50.0})
    sym_sector = {s: "IT" for s in ["A", "B", "C", "D", "E"]}
    result = sector_ranks(rs, sym_sector, top_n=3)
    assert len(result[0].top_stocks) <= 3


# ── SectorRank.to_dict ────────────────────────────────────────────────────────


def test_sector_rank_to_dict() -> None:
    rank = SectorRank(
        sector="IT",
        rs_median=75.0,
        rs_mean=72.0,
        stock_count=10,
        buy_count=4,
        buy_pct=40.0,
        top_stocks=["TCS", "INFY"],
        trend="LEADING",
    )
    d = rank.to_dict()
    assert d["sector"] == "IT"
    assert d["rs_median"] == 75.0
    assert d["trend"] == "LEADING"
    assert "TCS" in d["top_stocks"]


# ── rotation_signal ───────────────────────────────────────────────────────────


def test_rotation_signal_gaining() -> None:
    current = [SectorRank("IT", 80.0, 80.0, 5)]
    previous = [SectorRank("IT", 70.0, 70.0, 5)]
    result = rotation_signal(current, previous)
    assert result["IT"] == "GAINING"


def test_rotation_signal_losing() -> None:
    current = [SectorRank("Banks", 50.0, 50.0, 5)]
    previous = [SectorRank("Banks", 65.0, 65.0, 5)]
    result = rotation_signal(current, previous)
    assert result["Banks"] == "LOSING"


def test_rotation_signal_stable() -> None:
    current = [SectorRank("Pharma", 60.0, 60.0, 5)]
    previous = [SectorRank("Pharma", 61.0, 61.0, 5)]
    result = rotation_signal(current, previous)
    assert result["Pharma"] == "STABLE"


def test_rotation_signal_new_sector() -> None:
    current = [SectorRank("FMCG", 70.0, 70.0, 3)]
    previous: list[SectorRank] = []
    result = rotation_signal(current, previous)
    assert result["FMCG"] == "NEW"
