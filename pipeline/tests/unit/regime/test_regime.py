"""
Unit tests for marketpulse.regime — no network calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from marketpulse.regime import RegimeFilter, _classify


def test_classify_bull() -> None:
    label, mult = _classify(5.0)
    assert label == "Bull"
    assert mult == 1.0


def test_classify_bear() -> None:
    label, mult = _classify(-5.0)
    assert label == "Bear"
    assert mult == 0.25


def test_classify_sideways() -> None:
    label, mult = _classify(1.0)
    assert label == "Sideways"
    assert mult == 0.5


@patch("yfinance.download")
def test_regime_filter_uses_fresh_cache(mock_download: MagicMock, tmp_path: Path) -> None:
    cache_file = tmp_path / "nifty_cache.parquet"
    df = pd.DataFrame({"Close": [20000.0, 20100.0]}, index=pd.date_range("2026-07-01", periods=2))
    df.to_parquet(cache_file)

    # We patch NIFTY_CACHE with a real file that exists and is fresh
    with patch("marketpulse.regime.NIFTY_CACHE", cache_file):
        rf = RegimeFilter(force_download=False)

        # Should load from cache and build indicators
        mock_download.assert_not_called()
        assert len(rf.get_nifty_close()) == 2
        assert rf.get_nifty_close().iloc[-1] == 20100.0


@patch("yfinance.download")
def test_regime_filter_downloads_on_missing_or_stale_cache(
    mock_download: MagicMock, tmp_path: Path
) -> None:
    cache_file = tmp_path / "nifty_cache.parquet"

    # Mock yfinance return value
    df = pd.DataFrame({"Close": [100.0] * 210}, index=pd.date_range("2026-01-01", periods=210))
    mock_download.return_value = df

    with patch("marketpulse.regime.NIFTY_CACHE", cache_file):
        rf = RegimeFilter(force_download=False)
        mock_download.assert_called_once()
        assert len(rf.get_nifty_close()) == 210
        assert cache_file.exists()


@patch("yfinance.download")
def test_regime_filter_classification(mock_download: MagicMock, tmp_path: Path) -> None:
    # Generate 250 days of data: EMA200 will be around 100
    # First 200 days = 100, last day = 120 (Bull)
    prices = [100.0] * 249 + [120.0]
    df = pd.DataFrame({"Close": prices}, index=pd.date_range("2026-01-01", periods=250))
    mock_download.return_value = df

    cache_file = tmp_path / "nifty_cache.parquet"
    with patch("marketpulse.regime.NIFTY_CACHE", cache_file):
        rf = RegimeFilter(force_download=True)
        regime, mult = rf.get_current_regime()
        assert regime == "Bull"
        assert mult == 1.0


@patch("yfinance.download")
def test_regime_filter_saves_json(mock_download: MagicMock, tmp_path: Path) -> None:
    prices = [100.0] * 249 + [120.0]
    df = pd.DataFrame({"Close": prices}, index=pd.date_range("2026-01-01", periods=250))
    mock_download.return_value = df

    cache_file = tmp_path / "nifty_cache.parquet"
    out_dir = tmp_path / "scan_results"
    out_dir.mkdir()

    with (
        patch("marketpulse.regime.NIFTY_CACHE", cache_file),
        patch("marketpulse.regime.OUTPUT_DIR", out_dir),
    ):
        rf = RegimeFilter(force_download=True)
        out_path = rf.save_regime_json()

        assert out_path.exists()
        with out_path.open() as fh:
            data = json.load(fh)
            assert data["regime"] == "Bull"
            assert data["nifty_close"] == 120.0
            assert "regime_breakdown_52w" in data
