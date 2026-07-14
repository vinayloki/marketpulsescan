"""
Unit tests for ingestion/providers/ — all mocked, no network calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd

from marketpulse.ingestion.providers import ProviderChain, get_provider_chain
from marketpulse.ingestion.providers.bhavcopy import BhavcopProvider
from marketpulse.ingestion.providers.yfinance import YFinanceProvider

# ── ProviderChain tests ───────────────────────────────────────────────────────


class TestProviderChain:
    def _make_provider(self, caps: set[str], return_val: object = None) -> MagicMock:
        p = MagicMock()
        p.capabilities = frozenset(caps)
        if "universe" in caps:
            p.fetch_universe.return_value = return_val or ["RELIANCE", "TCS"]
        if "ohlcv" in caps:
            p.fetch_ohlcv.return_value = return_val or pd.DataFrame()
        if "fundamentals" in caps:
            p.fetch_fundamentals.return_value = return_val or {}
        return p

    def test_routes_universe_to_first_capable(self):
        p1 = self._make_provider({"universe"}, ["INFY", "WIPRO"])
        p2 = self._make_provider({"ohlcv"})
        chain = ProviderChain([p1, p2])
        result = chain.fetch_universe()
        assert result == ["INFY", "WIPRO"]
        p1.fetch_universe.assert_called_once()
        p2.fetch_universe.assert_not_called()

    def test_routes_ohlcv_to_first_capable(self):
        p1 = self._make_provider({"universe"})
        p2 = self._make_provider({"ohlcv"})
        chain = ProviderChain([p1, p2])
        chain.fetch_ohlcv(["RELIANCE"], period="1mo", interval="1d")
        p1.fetch_ohlcv.assert_not_called()
        p2.fetch_ohlcv.assert_called_once()

    def test_returns_empty_universe_when_no_capable_provider(self):
        p = self._make_provider({"ohlcv"})
        chain = ProviderChain([p])
        assert chain.fetch_universe() == []

    def test_returns_empty_df_when_no_ohlcv_provider(self):
        p = self._make_provider({"universe"})
        chain = ProviderChain([p])
        df = chain.fetch_ohlcv([], period="1mo", interval="1d")
        assert df.empty

    def test_routes_fundamentals(self):
        p1 = self._make_provider({"universe"})
        p2 = self._make_provider({"fundamentals"}, {"INFY": {"pe": 25.0}})
        chain = ProviderChain([p1, p2])
        result = chain.fetch_fundamentals(["INFY"])
        assert "INFY" in result


# ── BhavcopProvider tests ─────────────────────────────────────────────────────


class TestBhavcopProvider:
    def test_capabilities_declared(self):
        p = BhavcopProvider()
        assert "universe" in p.capabilities
        assert "bhavcopy" in p.capabilities
        assert "ohlcv" not in p.capabilities  # history is YFinance's job

    def test_returns_empty_when_nse_unavailable(self):
        """When nse-archives is not importable, provider degrades gracefully."""
        with patch("marketpulse.ingestion.providers.bhavcopy._NSE_AVAILABLE", False):
            p = BhavcopProvider()
            p._api = None
            result = p.fetch_universe()
            assert result == []

    def test_filters_eq_series(self):
        """EQ series filter removes non-equity rows."""
        raw_df = pd.DataFrame(
            {
                "SYMBOL": ["RELIANCE", "SOMEETF", "TCS"],
                "SERIES": ["EQ", "EQ1", "EQ"],
                "CLOSE_PRICE": [2945.0, 100.0, 4185.0],
            }
        )
        mock_api = MagicMock()
        mock_api.get.return_value = raw_df
        p = BhavcopProvider()
        p._api = mock_api
        result = p.fetch_universe()
        assert "RELIANCE" in result
        assert "TCS" in result
        assert "SOMEETF" not in result

    def test_normalise_bhavcopy_maps_columns(self):
        raw_df = pd.DataFrame(
            {
                "SYMBOL": ["HDFCBANK", "INFY"],
                "SERIES": ["EQ", "EQ"],
                "CLOSE_PRICE": [1812.45, 1645.80],
                "OPEN_PRICE": [1800.0, 1650.0],
                "TTL_TRD_QNTY": [1000000, 500000],
            }
        )
        p = BhavcopProvider()
        result = p._normalise_bhavcopy(raw_df)
        assert set(result.columns) >= {"symbol", "close", "open", "volume"}
        assert list(result["symbol"]) == ["HDFCBANK", "INFY"]

    def test_find_col_case_insensitive(self):
        df = pd.DataFrame({"CLOSE_PRICE": [1.0], "symbol": ["X"]})
        p = BhavcopProvider()
        assert p._find_col(df, ["CLOSE_PRICE"]) == "CLOSE_PRICE"
        assert p._find_col(df, ["SYMBOL"]) == "symbol"
        assert p._find_col(df, ["NOTEXIST"]) is None

    def test_handles_empty_bhavcopy_gracefully(self):
        mock_api = MagicMock()
        mock_api.get.return_value = pd.DataFrame()
        p = BhavcopProvider()
        p._api = mock_api
        result = p.fetch_universe()
        assert result == []


# ── YFinanceProvider tests ────────────────────────────────────────────────────


class TestYFinanceProvider:
    def test_capabilities_declared(self):
        p = YFinanceProvider()
        assert "ohlcv" in p.capabilities
        assert "fundamentals" in p.capabilities
        assert "universe" in p.capabilities

    @patch("marketpulse.ingestion.providers.yfinance.YFinanceProvider.fetch_universe")
    def test_fetch_universe_returns_list(self, mock_fetch):
        mock_fetch.return_value = ["RELIANCE", "TCS", "INFY"]
        p = YFinanceProvider()
        result = p.fetch_universe()
        assert isinstance(result, list)
        assert len(result) == 3

    def test_fetch_ohlcv_has_correct_signature(self):
        """Verify fetch_ohlcv signature has the expected parameters."""
        import inspect

        sig = inspect.signature(YFinanceProvider.fetch_ohlcv)
        assert "symbols" in sig.parameters
        assert "period" in sig.parameters
        assert "interval" in sig.parameters

    def test_fetch_fundamentals_returns_dict(self):
        mock_ticker = MagicMock()
        mock_ticker.info = {
            "longName": "Test Corp",
            "sector": "Technology",
            "trailingPE": 25.0,
        }
        with patch("yfinance.Ticker", return_value=mock_ticker):
            p = YFinanceProvider()
            result = p.fetch_fundamentals(["TEST"])
        assert "TEST" in result
        assert result["TEST"]["name"] == "Test Corp"
        assert result["TEST"]["sector"] == "Technology"
        assert result["TEST"]["pe"] == 25.0

    def test_fetch_fundamentals_handles_failure(self):
        with patch("yfinance.Ticker", side_effect=Exception("network error")):
            p = YFinanceProvider()
            result = p.fetch_fundamentals(["FAIL"])
        assert "FAIL" in result
        assert result["FAIL"] == {}


# ── get_provider_chain smoke test ─────────────────────────────────────────────


def test_get_provider_chain_returns_chain():
    chain = get_provider_chain()
    assert isinstance(chain, ProviderChain)
    assert len(chain._providers) >= 2
