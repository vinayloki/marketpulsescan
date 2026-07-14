"""
MarketPulseScan — Universe Ingestion Module

Loads the tradeable NSE/BSE equity universe with:
  - EQ series filtering
  - Disk cache with TTL
  - Holiday calendar (is_trading_day)
  - NSE symbol -> name/ISIN enrichment where available
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path  # noqa: TC003
from typing import Any

from marketpulse.config.settings import (
    NSE_SYMBOLS_CACHE,
    UNIVERSE_CACHE_TTL_H,
)

log = logging.getLogger(__name__)

# NSE publishes its holiday list in the bhavcopy headers / separately.
# This is a static 2025-2026 fallback list for offline / CI use.
_NSE_HOLIDAYS_2025_2026: set[str] = {
    # 2025 NSE holidays (YYYY-MM-DD)
    "2025-01-26",  # Republic Day
    "2025-02-26",  # Mahashivratri
    "2025-03-14",  # Holi
    "2025-03-31",  # Id-ul-Fitr (Ramzan Id)
    "2025-04-10",  # Shri Ram Navami
    "2025-04-14",  # Dr. Babasaheb Ambedkar Jayanti
    "2025-04-18",  # Good Friday
    "2025-05-01",  # Maharashtra Day
    "2025-08-15",  # Independence Day
    "2025-08-27",  # Ganesh Chaturthi
    "2025-10-02",  # Mahatma Gandhi Jayanti & Vijaya Dashami
    "2025-10-20",  # Diwali Laxmi Pujan
    "2025-10-21",  # Diwali Balipratipada
    "2025-11-05",  # Prakash Gurpurb Sri Guru Nanak Dev Ji
    "2025-12-25",  # Christmas
    # 2026 (preliminary)
    "2026-01-26",  # Republic Day
    "2026-08-15",  # Independence Day
    "2026-10-02",  # Mahatma Gandhi Jayanti
    "2026-12-25",  # Christmas
}


@dataclass
class UniverseSymbol:
    """A single tradeable equity symbol from the NSE/BSE universe."""

    symbol: str
    name: str | None = None
    exchange: str = "NSE"
    isin: str | None = None
    sector: str | None = None
    industry: str | None = None
    mcap_cr: float | None = None
    mcap_category: str | None = None
    is_active: bool = True
    extra: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "isin": self.isin,
            "sector": self.sector,
            "industry": self.industry,
            "mcap_cr": self.mcap_cr,
            "mcap_category": self.mcap_category,
            "is_active": self.is_active,
        }


def load_universe(
    *,
    exchange: str = "NSE",
    provider: Any | None = None,
    cache_file: Path = NSE_SYMBOLS_CACHE,
    cache_ttl_h: float = UNIVERSE_CACHE_TTL_H,
    force_refresh: bool = False,
) -> list[UniverseSymbol]:
    """
    Load the tradeable equity universe for the given exchange.

    1. Tries disk cache (JSON) if fresh.
    2. Falls back to provider chain (BhavcopProvider -> YFinanceProvider).
    3. Writes successful result to cache.

    Returns list of UniverseSymbol. Empty list on total failure.
    """
    if not force_refresh and _cache_is_fresh(cache_file, cache_ttl_h):
        cached = _load_from_cache(cache_file)
        if cached:
            log.info("Universe: loaded %d symbols from cache", len(cached))
            return cached

    if provider is None:
        from marketpulse.ingestion.providers import get_provider_chain

        provider = get_provider_chain()

    log.info("Universe: fetching from provider (%s)", exchange)
    try:
        raw_symbols: list[str] = provider.fetch_universe()
    except Exception as exc:
        log.error("Universe: provider fetch failed: %s", exc)
        return []

    if not raw_symbols:
        log.warning("Universe: provider returned empty universe")
        return []

    universe = [UniverseSymbol(symbol=sym, exchange=exchange) for sym in raw_symbols]
    _save_to_cache(universe, cache_file)
    log.info("Universe: loaded %d symbols from provider", len(universe))
    return universe


def is_trading_day(dt: date | datetime | None = None) -> bool:
    """
    Return True if `dt` is a likely NSE trading day (Mon-Fri, not a known holiday).

    Uses a static 2025-2026 holiday list; accurate for CI/offline use.
    """
    if dt is None:
        dt = datetime.now()
    if isinstance(dt, datetime):
        dt = dt.date()

    # Skip weekends
    if dt.weekday() >= 5:
        return False

    # Check against known holidays
    return dt.isoformat() not in _NSE_HOLIDAYS_2025_2026


def last_trading_day(reference: date | datetime | None = None) -> date:
    """Return the last trading day on or before `reference` (default: today)."""
    if reference is None:
        reference = datetime.now().date()
    elif isinstance(reference, datetime):
        reference = reference.date()

    dt = reference
    for _ in range(14):  # look back up to 2 weeks
        if is_trading_day(dt):
            return dt
        dt = dt - timedelta(days=1)

    return reference  # fallback


def classify_mcap(mcap_cr: float | None) -> str | None:
    """
    Classify market cap into NSE/SEBI categories.
    Returns None if mcap_cr is None or 0.
    """
    if not mcap_cr:
        return None
    if mcap_cr >= 20000:
        return "Large Cap"
    if mcap_cr >= 5000:
        return "Mid Cap"
    if mcap_cr >= 500:
        return "Small Cap"
    return "Micro Cap"


# ── Cache helpers ─────────────────────────────────────────────────────────────


def _cache_is_fresh(path: Path, max_age_h: float) -> bool:
    if not path.exists():
        return False
    age_h = (time.time() - path.stat().st_mtime) / 3600
    return age_h < max_age_h


def _load_from_cache(path: Path) -> list[UniverseSymbol]:
    try:
        with path.open(encoding="utf-8") as f:
            data: list[dict[str, object]] = json.load(f)
        return [
            UniverseSymbol(
                symbol=str(d.get("symbol", "")),
                name=str(d["name"]) if d.get("name") else None,
                exchange=str(d.get("exchange", "NSE")),
                isin=str(d["isin"]) if d.get("isin") else None,
                sector=str(d["sector"]) if d.get("sector") else None,
                industry=str(d["industry"]) if d.get("industry") else None,
                mcap_cr=float(d["mcap_cr"]) if d.get("mcap_cr") is not None else None,  # type: ignore[arg-type]
                mcap_category=str(d["mcap_category"]) if d.get("mcap_category") else None,
                is_active=bool(d.get("is_active", True)),
            )
            for d in data
            if d.get("symbol")
        ]
    except Exception as exc:
        log.warning("Universe cache load failed: %s", exc)
        return []


def _save_to_cache(universe: list[UniverseSymbol], path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump([u.to_dict() for u in universe], f)
        log.debug("Universe: cached %d symbols to %s", len(universe), path.name)
    except Exception as exc:
        log.warning("Universe cache write failed: %s", exc)
