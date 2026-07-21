"""
Unit tests for technical/levels.py — support/resistance and pivot levels.
"""

from __future__ import annotations

import pandas as pd
import pytest

from marketpulse.technical.levels import (
    calculate_camarilla_pivots,
    calculate_classic_pivots,
    calculate_fibonacci_pivots,
    find_support_resistance,
)


@pytest.fixture
def sample_hlc() -> tuple[pd.Series, pd.Series, pd.Series]:
    high = pd.Series([105.0, 110.0, 108.0])
    low = pd.Series([95.0, 98.0, 96.0])
    close = pd.Series([100.0, 102.0, 101.0])
    return high, low, close


def test_calculate_classic_pivots(sample_hlc: tuple[pd.Series, pd.Series, pd.Series]) -> None:
    high, low, close = sample_hlc
    pivots = calculate_classic_pivots(high, low, close)

    # PP = (108 + 96 + 101) / 3 = 101.6666...
    assert abs(pivots["pivot"].iloc[-1] - 101.6666) < 0.001
    # R1 = 2 * PP - Low = 2 * 101.666... - 96 = 107.333...
    assert abs(pivots["r1"].iloc[-1] - 107.3333) < 0.001
    # S1 = 2 * PP - High = 2 * 101.666... - 108 = 95.333...
    assert abs(pivots["s1"].iloc[-1] - 95.3333) < 0.001


def test_calculate_fibonacci_pivots(sample_hlc: tuple[pd.Series, pd.Series, pd.Series]) -> None:
    high, low, close = sample_hlc
    pivots = calculate_fibonacci_pivots(high, low, close)

    # PP = 101.666...
    # R1 = PP + 0.382 * (High - Low) = 101.666... + 0.382 * 12 = 106.2506...
    assert abs(pivots["r1"].iloc[-1] - 106.2506) < 0.001


def test_calculate_camarilla_pivots(sample_hlc: tuple[pd.Series, pd.Series, pd.Series]) -> None:
    high, low, close = sample_hlc
    pivots = calculate_camarilla_pivots(high, low, close)

    # R3 = Close + (High - Low) * 1.1 / 4 = 101 + 12 * 1.1 / 4 = 101 + 3.3 = 104.3
    assert abs(pivots["r3"].iloc[-1] - 104.3) < 0.001


def test_find_support_resistance() -> None:
    # Build a series with clear double tops and double bottoms
    # Pattern: 100 -> 150 -> 100 -> 150 -> 100 -> 150 -> 100
    prices = []
    for _ in range(3):
        prices += list(range(100, 150, 5)) + list(range(150, 100, -5))
    prices += [100]

    high = pd.Series(prices)
    low = pd.Series(prices)

    # Find levels with window=3 (small window to capture the peaks/troughs)
    levels = find_support_resistance(high, low, window=3, min_touchpoints=2, tolerance_pct=2.0)

    # We expect 100 (bottoms) and 150 (tops) to be the key levels
    assert len(levels) >= 2
    assert any(abs(l - 100) < 5 for l in levels)
    assert any(abs(l - 150) < 5 for l in levels)
