"""
Unit tests for ingestion/universe.py — no network calls.
"""

from __future__ import annotations

import json
from datetime import date
from unittest.mock import MagicMock

import pytest

from marketpulse.ingestion.universe import (
    UniverseSymbol,
    classify_mcap,
    is_trading_day,
    last_trading_day,
    load_universe,
)

# ── UniverseSymbol ────────────────────────────────────────────────────────────


def test_universe_symbol_defaults():
    sym = UniverseSymbol(symbol="RELIANCE")
    assert sym.exchange == "NSE"
    assert sym.is_active is True
    assert sym.sector is None


def test_universe_symbol_to_dict():
    sym = UniverseSymbol(symbol="TCS", name="TCS Ltd", exchange="NSE")
    d = sym.to_dict()
    assert d["symbol"] == "TCS"
    assert d["name"] == "TCS Ltd"
    assert "sector" in d


# ── is_trading_day ────────────────────────────────────────────────────────────


def test_saturday_is_not_trading_day():
    # 2025-07-05 is a Saturday
    assert not is_trading_day(date(2025, 7, 5))


def test_sunday_is_not_trading_day():
    # 2025-07-06 is a Sunday
    assert not is_trading_day(date(2025, 7, 6))


def test_republic_day_is_not_trading_day():
    assert not is_trading_day(date(2025, 1, 26))


def test_regular_monday_is_trading_day():
    # 2025-07-07 is a Monday and not a known holiday
    assert is_trading_day(date(2025, 7, 7))


def test_christmas_is_not_trading_day():
    assert not is_trading_day(date(2025, 12, 25))


# ── last_trading_day ──────────────────────────────────────────────────────────


def test_last_trading_day_on_weekday_returns_same():
    # 2025-07-07 is a Monday
    result = last_trading_day(date(2025, 7, 7))
    assert result == date(2025, 7, 7)


def test_last_trading_day_on_saturday_returns_friday():
    # 2025-07-05 is Saturday → should return 2025-07-04 (Friday)
    result = last_trading_day(date(2025, 7, 5))
    assert result == date(2025, 7, 4)


def test_last_trading_day_on_sunday_returns_friday():
    result = last_trading_day(date(2025, 7, 6))
    assert result == date(2025, 7, 4)


# ── classify_mcap ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "mcap_cr,expected",
    [
        (25000.0, "Large Cap"),
        (20000.0, "Large Cap"),
        (10000.0, "Mid Cap"),
        (5000.0, "Mid Cap"),
        (1000.0, "Small Cap"),
        (200.0, "Micro Cap"),
        (0.0, None),
        (None, None),
    ],
)
def test_classify_mcap(mcap_cr, expected):
    assert classify_mcap(mcap_cr) == expected


# ── load_universe ─────────────────────────────────────────────────────────────


def test_load_universe_from_provider(tmp_path):
    mock_provider = MagicMock()
    mock_provider.fetch_universe.return_value = ["RELIANCE", "TCS", "INFY"]

    result = load_universe(
        provider=mock_provider,
        cache_file=tmp_path / "symbols.json",
        force_refresh=True,
    )

    assert len(result) == 3
    symbols = [u.symbol for u in result]
    assert "RELIANCE" in symbols
    assert "TCS" in symbols


def test_load_universe_writes_cache(tmp_path):
    mock_provider = MagicMock()
    mock_provider.fetch_universe.return_value = ["HDFCBANK"]
    cache_file = tmp_path / "symbols.json"

    load_universe(
        provider=mock_provider,
        cache_file=cache_file,
        force_refresh=True,
    )

    assert cache_file.exists()
    with cache_file.open() as f:
        data = json.load(f)
    assert any(d["symbol"] == "HDFCBANK" for d in data)


def test_load_universe_uses_cache_when_fresh(tmp_path):
    cache_file = tmp_path / "symbols.json"
    cached = [
        {
            "symbol": "CACHED",
            "name": None,
            "exchange": "NSE",
            "isin": None,
            "sector": None,
            "industry": None,
            "mcap_cr": None,
            "mcap_category": None,
            "is_active": True,
        }
    ]
    with cache_file.open("w") as f:
        json.dump(cached, f)

    mock_provider = MagicMock()

    result = load_universe(
        provider=mock_provider,
        cache_file=cache_file,
        cache_ttl_h=24.0,
        force_refresh=False,
    )

    mock_provider.fetch_universe.assert_not_called()
    assert result[0].symbol == "CACHED"


def test_load_universe_returns_empty_on_provider_failure(tmp_path):
    mock_provider = MagicMock()
    mock_provider.fetch_universe.side_effect = Exception("network error")

    result = load_universe(
        provider=mock_provider,
        cache_file=tmp_path / "symbols.json",
        force_refresh=True,
    )

    assert result == []


def test_load_universe_returns_empty_when_provider_returns_empty(tmp_path):
    mock_provider = MagicMock()
    mock_provider.fetch_universe.return_value = []

    result = load_universe(
        provider=mock_provider,
        cache_file=tmp_path / "symbols.json",
        force_refresh=True,
    )

    assert result == []
