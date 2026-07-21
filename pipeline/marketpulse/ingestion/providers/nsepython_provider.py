"""
NSEPython Provider — standardized official NSE data source.

Wraps the `nsepython` package (https://pypi.org/project/nsepython/) which
talks to NSE's own endpoints with proper session/cookie handling:
  - fetch_universe:      nse_eq_symbols() — all EQ-series symbols
  - fetch_universe_meta: EQUITY_L.csv     — company name, ISIN, listing date

Sector/industry/mcap are NOT in the NSE equity master; those come from the
fundamentals snapshot (see ingestion.universe.enrich_universe) until the
Sprint 3 fundamentals module lands.

Never raises from fetch_* methods — logs and returns empty on failure,
so the ProviderChain can fall through to the next provider.
"""

from __future__ import annotations

import csv
import io
import logging

log = logging.getLogger(__name__)

_EQUITY_MASTER_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"


class NSEPythonProvider:
    """Universe + symbol-metadata provider backed by nsepython / NSE archives."""

    capabilities: frozenset[str] = frozenset({"universe", "universe_meta"})

    def fetch_universe(self) -> list[str]:
        """Return sorted list of NSE EQ-series ticker symbols (no .NS suffix)."""
        try:
            from nsepython import nse_eq_symbols

            symbols = nse_eq_symbols()
        except Exception as exc:
            log.warning("NSEPythonProvider: universe fetch failed: %s", exc)
            return []

        clean = sorted({s.strip().upper() for s in symbols if s and s.strip()})
        log.info("NSEPythonProvider: %d EQ symbols from NSE", len(clean))
        return clean

    def fetch_universe_meta(self) -> dict[str, dict[str, object]]:
        """
        Return {symbol: {"name", "isin", "listing_date"}} from the official
        NSE equity master (EQUITY_L.csv). Empty dict on failure.
        """
        try:
            import requests
            from nsepython import nsefetch  # session-managed fetch  # noqa: F401

            headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
            resp = requests.get(_EQUITY_MASTER_URL, headers=headers, timeout=30)
            resp.raise_for_status()
        except Exception as exc:
            log.warning("NSEPythonProvider: equity master fetch failed: %s", exc)
            return {}

        meta: dict[str, dict[str, object]] = {}
        try:
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                # Header names carry leading spaces in the NSE file
                cleaned = {k.strip(): (v.strip() if v else v) for k, v in row.items()}
                symbol = (cleaned.get("SYMBOL") or "").upper()
                if not symbol or cleaned.get("SERIES") != "EQ":
                    continue
                meta[symbol] = {
                    "name": cleaned.get("NAME OF COMPANY") or None,
                    "isin": cleaned.get("ISIN NUMBER") or None,
                    "listing_date": cleaned.get("DATE OF LISTING") or None,
                }
        except Exception as exc:
            log.warning("NSEPythonProvider: equity master parse failed: %s", exc)
            return {}

        log.info("NSEPythonProvider: metadata for %d symbols", len(meta))
        return meta
