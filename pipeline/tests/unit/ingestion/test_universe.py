"""
Unit tests for ingestion/universe.py — no network calls.
"""

from __future__ import annotations

import json
from pathlib import Path
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


# ── enrich_universe ───────────────────────────────────────────────────────────


def test_enrich_universe_from_snapshot(tmp_path: Path) -> None:
    from marketpulse.ingestion.universe import UniverseSymbol, enrich_universe

    snapshot = tmp_path / "fundamentals.json"
    snapshot.write_text(
        json.dumps(
            {
                "stocks": [
                    {
                        "s": "ABC",
                        "name": "ABC Ltd",
                        "sector": "IT & Technology",
                        "ind": "Software",
                        "mcap": 55000.0,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    universe = [UniverseSymbol(symbol="ABC"), UniverseSymbol(symbol="XYZ")]
    enriched = enrich_universe(universe, snapshot_file=snapshot)

    assert enriched == 1
    assert universe[0].name == "ABC Ltd"
    assert universe[0].sector == "IT & Technology"
    assert universe[0].mcap_cr == 55000.0
    assert universe[0].mcap_category is not None
    assert universe[1].name is None


def test_enrich_universe_missing_file_is_noop(tmp_path: Path) -> None:
    from marketpulse.ingestion.universe import UniverseSymbol, enrich_universe

    universe = [UniverseSymbol(symbol="ABC")]
    assert enrich_universe(universe, snapshot_file=tmp_path / "nope.json") == 0
    assert universe[0].name is None


def test_enrich_universe_does_not_overwrite_existing(tmp_path: Path) -> None:
    from marketpulse.ingestion.universe import UniverseSymbol, enrich_universe

    snapshot = tmp_path / "fundamentals.json"
    snapshot.write_text(
        json.dumps({"stocks": [{"s": "ABC", "name": "Snapshot Name", "sector": "Others"}]}),
        encoding="utf-8",
    )
    universe = [UniverseSymbol(symbol="ABC", name="Official Name")]
    enrich_universe(universe, snapshot_file=snapshot)
    assert universe[0].name == "Official Name"  # official NSE name wins
    assert universe[0].sector == "Others"


def test_enrich_universe_falls_back_to_provider(tmp_path: Path) -> None:
    """When no snapshot exists, enrich_universe uses the provider chain."""
    from marketpulse.ingestion.universe import UniverseSymbol, enrich_universe

    mock_provider = MagicMock()
    mock_provider.fetch_fundamentals.return_value = {
        "ABC": {
            "name": "ABC Corp",
            "sector": "Technology",
            "industry": "Software",
            "mcap": 12000.0,
        },
    }

    universe = [UniverseSymbol(symbol="ABC"), UniverseSymbol(symbol="XYZ")]
    enriched = enrich_universe(
        universe,
        snapshot_file=tmp_path / "nope.json",  # does not exist
        provider=mock_provider,
    )

    assert enriched == 1
    assert universe[0].name == "ABC Corp"
    assert universe[0].sector == "Technology"
    assert universe[0].industry == "Software"
    assert universe[0].mcap_cr == 12000.0
    assert universe[0].mcap_category == "Mid Cap"
    assert universe[1].sector is None  # not in provider response
    mock_provider.fetch_fundamentals.assert_called_once()


def test_enrich_universe_snapshot_beats_provider(tmp_path: Path) -> None:
    """When a snapshot exists, provider is NOT called even if passed."""
    from marketpulse.ingestion.universe import UniverseSymbol, enrich_universe

    snapshot = tmp_path / "fundamentals.json"
    snapshot.write_text(
        json.dumps({"stocks": [{"s": "ABC", "name": "From Snapshot", "sector": "Finance"}]}),
        encoding="utf-8",
    )

    mock_provider = MagicMock()
    mock_provider.fetch_fundamentals.return_value = {
        "ABC": {"name": "From Provider", "sector": "Tech"},
    }

    universe = [UniverseSymbol(symbol="ABC")]
    enrich_universe(universe, snapshot_file=snapshot, provider=mock_provider)

    assert universe[0].name == "From Snapshot"
    assert universe[0].sector == "Finance"
    mock_provider.fetch_fundamentals.assert_not_called()


def test_enrich_universe_provider_exception_is_noop(tmp_path: Path) -> None:
    """Provider failure doesn't raise — returns 0."""
    from marketpulse.ingestion.universe import UniverseSymbol, enrich_universe

    mock_provider = MagicMock()
    mock_provider.fetch_fundamentals.side_effect = RuntimeError("API down")

    universe = [UniverseSymbol(symbol="ABC")]
    result = enrich_universe(
        universe,
        snapshot_file=tmp_path / "nope.json",
        provider=mock_provider,
    )
    assert result == 0
    assert universe[0].sector is None


def test_enrich_universe_provider_skips_already_enriched(tmp_path: Path) -> None:
    """Provider only fetches symbols missing sector data."""
    from marketpulse.ingestion.universe import UniverseSymbol, enrich_universe

    mock_provider = MagicMock()
    mock_provider.fetch_fundamentals.return_value = {}

    universe = [UniverseSymbol(symbol="ABC", sector="Already Set")]
    enrich_universe(
        universe,
        snapshot_file=tmp_path / "nope.json",
        provider=mock_provider,
    )
    # All symbols already have sector → no fetch needed
    mock_provider.fetch_fundamentals.assert_not_called()


def test_load_universe_passes_provider_to_enrich(tmp_path: Path) -> None:
    """load_universe wires its provider into enrich_universe."""
    from marketpulse.ingestion.universe import load_universe

    mock_provider = MagicMock()
    mock_provider.fetch_universe.return_value = ["ABC"]
    mock_provider.fetch_universe_meta.return_value = {}
    mock_provider.fetch_fundamentals.return_value = {
        "ABC": {"name": "Live Name", "sector": "Healthcare", "industry": "Pharma", "mcap": 800.0},
    }

    result = load_universe(
        provider=mock_provider,
        cache_file=tmp_path / "symbols.json",
        force_refresh=True,
    )

    assert len(result) == 1
    assert result[0].sector == "Healthcare"
    assert result[0].industry == "Pharma"
    mock_provider.fetch_fundamentals.assert_called_once()
