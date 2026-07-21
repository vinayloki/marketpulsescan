"""Support/resistance and pivot level detection.

Provides functions to calculate pivot points (Classic, Fibonacci, Camarilla)
and identify support/resistance zones from historical price actions.
"""

from __future__ import annotations

import pandas as pd


def calculate_classic_pivots(
    high: pd.Series, low: pd.Series, close: pd.Series
) -> dict[str, pd.Series]:
    """
    Calculate daily/rolling classic pivot points.
    All inputs and outputs are pd.Series aligned to the same index.

    Formula:
        PP = (High + Low + Close) / 3
        R1 = 2 * PP - Low
        S1 = 2 * PP - High
        R2 = PP + (High - Low)
        S2 = PP - (High - Low)
        R3 = High + 2 * (PP - Low)
        S3 = Low - 2 * (High - PP)
    """
    pp = (high + low + close) / 3.0
    r1 = 2.0 * pp - low
    s1 = 2.0 * pp - high
    r2 = pp + (high - low)
    s2 = pp - (high - low)
    r3 = high + 2.0 * (pp - low)
    s3 = low - 2.0 * (high - pp)

    return {
        "pivot": pp,
        "r1": r1,
        "s1": s1,
        "r2": r2,
        "s2": s2,
        "r3": r3,
        "s3": s3,
    }


def calculate_fibonacci_pivots(
    high: pd.Series, low: pd.Series, close: pd.Series
) -> dict[str, pd.Series]:
    """
    Calculate daily/rolling Fibonacci pivot points.

    Formula:
        PP = (High + Low + Close) / 3
        R1 = PP + 0.382 * (High - Low)
        S1 = PP - 0.382 * (High - Low)
        R2 = PP + 0.618 * (High - Low)
        S2 = PP - 0.618 * (High - Low)
        R3 = PP + 1.000 * (High - Low)
        S3 = PP - 1.000 * (High - Low)
    """
    pp = (high + low + close) / 3.0
    diff = high - low
    r1 = pp + 0.382 * diff
    s1 = pp - 0.382 * diff
    r2 = pp + 0.618 * diff
    s2 = pp - 0.618 * diff
    r3 = pp + diff
    s3 = pp - diff

    return {
        "pivot": pp,
        "r1": r1,
        "s1": s1,
        "r2": r2,
        "s2": s2,
        "r3": r3,
        "s3": s3,
    }


def calculate_camarilla_pivots(
    high: pd.Series, low: pd.Series, close: pd.Series
) -> dict[str, pd.Series]:
    """
    Calculate Camarilla pivot points.

    Formula:
        PP = (High + Low + Close) / 3
        R4 = Close + (High - Low) * 1.1 / 2
        R3 = Close + (High - Low) * 1.1 / 4
        R2 = Close + (High - Low) * 1.1 / 6
        R1 = Close + (High - Low) * 1.1 / 12
        S1 = Close - (High - Low) * 1.1 / 12
        S2 = Close - (High - Low) * 1.1 / 6
        S3 = Close - (High - Low) * 1.1 / 4
        S4 = Close - (High - Low) * 1.1 / 2
    """
    pp = (high + low + close) / 3.0
    diff = high - low
    r4 = close + diff * 1.1 / 2.0
    r3 = close + diff * 1.1 / 4.0
    r2 = close + diff * 1.1 / 6.0
    r1 = close + diff * 1.1 / 12.0
    s1 = close - diff * 1.1 / 12.0
    s2 = close - diff * 1.1 / 6.0
    s3 = close - diff * 1.1 / 4.0
    s4 = close - diff * 1.1 / 2.0

    return {
        "pivot": pp,
        "r4": r4,
        "r3": r3,
        "r2": r2,
        "r1": r1,
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4,
    }


def find_support_resistance(
    high: pd.Series,
    low: pd.Series,
    window: int = 20,
    min_touchpoints: int = 2,
    tolerance_pct: float = 1.0,
) -> list[float]:
    """
    Find major support and resistance levels from local price peaks/troughs.

    Identifies local maxima and minima within a rolling window, clusters them
    based on proximity (tolerance_pct), and filters to levels with at least
    min_touchpoints touches.

    Returns:
        Sorted list of significant price levels.
    """
    if len(high) < window or len(low) < window:
        return []

    # Find rolling local highs/lows
    local_highs = high.rolling(window=window * 2 + 1, center=True).max()
    local_lows = low.rolling(window=window * 2 + 1, center=True).min()

    # Identify exact peak indices
    peaks = high[high == local_highs].dropna().tolist()
    troughs = low[low == local_lows].dropna().tolist()
    candidates = sorted(peaks + troughs)

    if not candidates:
        return []

    # Group nearby levels (clustering)
    levels: list[float] = []
    for price in candidates:
        # Check if this price is close to any already identified level
        found = False
        for i, lvl in enumerate(levels):
            if abs(price - lvl) / lvl * 100 <= tolerance_pct:
                # Update the level to be the average of touchpoints
                levels[i] = (lvl + price) / 2.0
                found = True
                break
        if not found:
            levels.append(price)

    # Filter by minimum touchpoints (how many times price hit the zone)
    significant_levels = []
    for lvl in levels:
        touches = 0
        for price in candidates:
            if abs(price - lvl) / lvl * 100 <= tolerance_pct:
                touches += 1
        if touches >= min_touchpoints:
            significant_levels.append(round(lvl, 2))

    return sorted(significant_levels)
