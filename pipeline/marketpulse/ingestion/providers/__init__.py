"""
MarketPulseScan — Data Provider Protocol & Factory

Defines the typed provider contracts and the fallback chain factory.
Primary: BhavcopProvider (NSE archives, official EOD data)
Fallback: YFinanceProvider (yfinance, full history + fundamentals)
"""

from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

import pandas as pd

log = logging.getLogger(__name__)


# ── Provider Protocols ────────────────────────────────────────────────────────


@runtime_checkable
class UniverseProvider(Protocol):
    """Provides the tradeable symbol universe."""

    capabilities: frozenset[str]

    def fetch_universe(self) -> list[str]:
        """Return sorted list of valid NSE equity ticker symbols (no .NS suffix)."""
        ...


@runtime_checkable
class OHLCVProvider(Protocol):
    """Provides OHLCV price history."""

    capabilities: frozenset[str]

    def fetch_ohlcv(
        self,
        symbols: list[str],
        *,
        period: str = "13mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Return a MultiIndex DataFrame: columns = (field, symbol).
        Fields: Open, High, Low, Close, Volume.
        Must never raise — return empty DataFrame on total failure.
        """
        ...


@runtime_checkable
class FundamentalsProvider(Protocol):
    """Provides fundamental data."""

    capabilities: frozenset[str]

    def fetch_fundamentals(
        self,
        symbols: list[str],
    ) -> dict[str, dict[str, object]]:
        """
        Return {symbol: {field: value}} for each symbol.
        Missing fields must be None, not omitted.
        Must never raise — return {} on total failure.
        """
        ...


# ── Provider Chain ────────────────────────────────────────────────────────────


class ProviderChain:
    """
    Ordered list of providers. Each capability (universe / ohlcv / fundamentals)
    is served by the first provider in the chain that declares it.
    """

    def __init__(self, providers: list[Any]) -> None:
        self._providers: list[Any] = providers

    def _first(self, capability: str) -> Any:
        for p in self._providers:
            caps: frozenset[str] = getattr(p, "capabilities", frozenset())
            if capability in caps:
                return p
        return None

    def fetch_universe(self) -> list[str]:
        p = self._first("universe")
        if p is None:
            log.error("No universe provider in chain")
            return []
        result: list[str] = p.fetch_universe()
        return result

    def fetch_ohlcv(
        self,
        symbols: list[str],
        *,
        period: str = "13mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        p = self._first("ohlcv")
        if p is None:
            log.error("No OHLCV provider in chain")
            return pd.DataFrame()
        df: pd.DataFrame = p.fetch_ohlcv(symbols, period=period, interval=interval)
        return df

    def fetch_universe_meta(self) -> dict[str, dict[str, object]]:
        p = self._first("universe_meta")
        if p is None:
            log.debug("No universe_meta provider in chain")
            return {}
        result: dict[str, dict[str, object]] = p.fetch_universe_meta()
        return result

    def fetch_fundamentals(
        self,
        symbols: list[str],
    ) -> dict[str, dict[str, object]]:
        p = self._first("fundamentals")
        if p is None:
            log.error("No fundamentals provider in chain")
            return {}
        result: dict[str, dict[str, object]] = p.fetch_fundamentals(symbols)
        return result


def get_provider_chain() -> ProviderChain:
    """
    Build the standard provider chain for production use.

    Chain (in priority order):
      1. NSEPythonProvider — universe + symbol metadata (nsepython, official NSE)
      2. BhavcopProvider   — universe fallback + bhavcopy OHLCV (NSE archives)
      3. YFinanceProvider  — ohlcv history + fundamentals (fallback)

    Each provider declares its capabilities; ProviderChain routes accordingly.
    """
    from marketpulse.ingestion.providers.bhavcopy import BhavcopProvider
    from marketpulse.ingestion.providers.bse_provider import BSEProvider
    from marketpulse.ingestion.providers.nsepython_provider import NSEPythonProvider
    from marketpulse.ingestion.providers.screener_provider import ScreenerProvider
    from marketpulse.ingestion.providers.yfinance import YFinanceProvider

    return ProviderChain(
        [
            NSEPythonProvider(),
            BSEProvider(),
            ScreenerProvider(),
            BhavcopProvider(),
            YFinanceProvider(),
        ]
    )
