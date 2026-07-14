"""
Unit tests for ingestion/ohlcv.py — mocked, no network calls.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import numpy as np
import pandas as pd

from marketpulse.ingestion.ohlcv import (
    _cache_is_fresh,
    compute_returns,
    extract_close_series,
    fetch_ohlcv,
)

# ── Cache helpers ─────────────────────────────────────────────────────────────


def test_cache_is_fresh_returns_false_for_missing_file(tmp_path):
    assert not _cache_is_fresh(tmp_path / "nofile.parquet", 24.0)


def test_cache_is_fresh_returns_true_for_new_file(tmp_path):
    f = tmp_path / "cache.parquet"
    f.write_bytes(b"x")
    assert _cache_is_fresh(f, 24.0)


def test_cache_is_fresh_returns_false_for_old_file(tmp_path):
    f = tmp_path / "cache.parquet"
    f.write_bytes(b"x")
    # Backdate the mtime by 25 hours
    old_time = time.time() - 25 * 3600
    import os

    os.utime(f, (old_time, old_time))
    assert not _cache_is_fresh(f, 24.0)


# ── fetch_ohlcv with mock provider ───────────────────────────────────────────


def _make_mock_df() -> pd.DataFrame:
    idx = pd.date_range("2025-01-01", periods=50, freq="B")
    syms = ["RELIANCE", "TCS"]
    arrays = [
        np.repeat(["Close", "Volume"], len(syms)),
        np.tile(syms, 2),
    ]
    cols = pd.MultiIndex.from_arrays(arrays)
    data = np.random.rand(50, len(syms) * 2)
    return pd.DataFrame(data, index=idx, columns=cols)


def test_fetch_ohlcv_from_provider(tmp_path):
    mock_df = _make_mock_df()
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = mock_df

    result = fetch_ohlcv(
        ["RELIANCE", "TCS"],
        cache_file=tmp_path / "cache.parquet",
        force_refresh=True,
        provider=mock_provider,
    )
    assert not result.empty
    mock_provider.fetch_ohlcv.assert_called_once()


def test_fetch_ohlcv_uses_cache_on_second_call(tmp_path):
    mock_df = _make_mock_df()
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = mock_df
    cache_file = tmp_path / "cache.parquet"

    # First call — writes cache
    fetch_ohlcv(
        ["RELIANCE", "TCS"], cache_file=cache_file, force_refresh=True, provider=mock_provider
    )
    # Second call — should use cache
    fetch_ohlcv(
        ["RELIANCE", "TCS"], cache_file=cache_file, force_refresh=False, provider=mock_provider
    )

    # Provider should only have been called once
    assert mock_provider.fetch_ohlcv.call_count == 1


def test_fetch_ohlcv_returns_empty_on_provider_failure(tmp_path):
    mock_provider = MagicMock()
    mock_provider.fetch_ohlcv.return_value = pd.DataFrame()

    result = fetch_ohlcv(
        ["FAIL"],
        cache_file=tmp_path / "cache.parquet",
        force_refresh=True,
        provider=mock_provider,
    )
    assert result.empty


# ── extract_close_series ──────────────────────────────────────────────────────


def test_extract_close_series_from_multiindex():
    idx = pd.date_range("2025-01-01", periods=10, freq="B")
    prices = pd.Series(range(10), index=idx, dtype=float)
    pd.MultiIndex.from_arrays([["Close"] * 10, ["RELIANCE"] * 10])
    df = pd.DataFrame({("Close", "RELIANCE"): prices})
    result = extract_close_series(df, "RELIANCE")
    assert len(result) == 10


def test_extract_close_series_returns_empty_for_missing_symbol():
    df = pd.DataFrame()
    result = extract_close_series(df, "MISSING")
    assert result.empty


# ── compute_returns ───────────────────────────────────────────────────────────


def test_compute_returns_all_timeframes():
    idx = pd.date_range("2024-01-01", periods=300, freq="B")
    # Monotonically increasing prices: easy to verify
    close = pd.Series(range(100, 400), index=idx, dtype=float)
    returns = compute_returns(close)
    assert "1D" in returns
    assert "1M" in returns
    assert "12M" in returns
    # All returns should be positive (prices always going up)
    for k, v in returns.items():
        assert v is not None and v > 0, f"{k}: expected positive return, got {v}"


def test_compute_returns_none_when_insufficient_data():
    close = pd.Series([100.0, 101.0, 102.0])  # only 3 points
    returns = compute_returns(close)
    # 12M requires 253 points — should be None
    assert returns["12M"] is None
    # 1D requires 2 points — should be non-None
    assert returns["1D"] is not None


def test_compute_returns_empty_series():
    close = pd.Series(dtype=float)
    returns = compute_returns(close)
    assert all(v is None for v in returns.values())
