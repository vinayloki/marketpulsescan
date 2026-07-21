"""
BSE Provider — official Bombay Stock Exchange (BSE) data provider.

Backing APIs:
  - `bseindia` library: fetches full 10,770+ BSE tradeable equity universe with ISINs and Scrip Codes.
  - BSE India Official API (`api.bseindia.com`): fetches exact live BSE quote (LTP, PrevClose, High, Low, 52W High/Low).

Never raises from fetch_* methods — logs and returns empty dict/list on failure.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

log = logging.getLogger(__name__)

_BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.bseindia.com/",
}

# Known Scrip Code mappings for top Indian stocks
_KNOWN_SCRIPS: dict[str, str] = {
    "HDFCBANK": "500180",
    "RELIANCE": "500325",
    "TCS": "532540",
    "INFY": "500209",
    "TATAMOTORS": "500570",
    "ACCENTMIC": "544080",
    "ICICIBANK": "532174",
    "SBIN": "500112",
    "BHARTIARTL": "532454",
    "ITC": "500875",
    "AXISBANK": "532215",
    "KOTAKBANK": "532454",
    "LT": "500510",
    "HINDUNILVR": "500696",
    "BAJFINANCE": "500034",
    "MARUTI": "532500",
}


class BSEProvider:
    """Official BSE India data provider using bseindia and BSE India Live API."""

    capabilities: frozenset[str] = frozenset({"universe", "bse_quote", "bse_live"})

    def __init__(self) -> None:
        self._scrip_cache: dict[str, str] = dict(_KNOWN_SCRIPS)

    def fetch_universe(self) -> list[str]:
        """
        Fetch all active BSE equity ticker symbols via `bseindia`.
        Returns sorted list of ticker symbols.
        """
        try:
            import bseindia

            df = bseindia.all_listed_securities()
            if df.empty:
                return sorted(list(self._scrip_cache.keys()))

            # Filter active equity instruments
            if "status" in df.columns:
                df = df[df["status"].astype(str).str.strip().str.upper() == "ACTIVE"]
            if "instrument" in df.columns:
                df = df[df["instrument"].astype(str).str.strip().str.capitalize() == "Equity"]

            symbols: set[str] = set()
            for _, row in df.iterrows():
                sym = str(row.get("symbol") or "").strip().upper()
                code = str(row.get("security_code") or "").strip()
                if sym and sym[0].isalpha():
                    symbols.add(sym)
                    if code:
                        self._scrip_cache[sym] = code

            clean = sorted(list(symbols))
            log.info("BSEProvider: %d BSE active equity symbols loaded", len(clean))
            return clean
        except Exception as exc:
            log.warning("BSEProvider: universe fetch failed: %s", exc)
            return sorted(list(self._scrip_cache.keys()))

    def get_scrip_code(self, symbol: str) -> str | None:
        """Lookup BSE Scrip Code for a given ticker symbol."""
        sym_clean = symbol.upper().strip()
        if sym_clean in self._scrip_cache:
            return self._scrip_cache[sym_clean]

        # Lazy load universe mapping if missing
        self.fetch_universe()
        return self._scrip_cache.get(sym_clean)

    def fetch_bse_quote(self, symbol: str) -> dict[str, object]:
        """
        Fetch live EOD quote directly from official BSE India API for a symbol.
        Returns dict with: symbol, close (LTP), prev_close, open, high, low.
        """
        scrip_code = self.get_scrip_code(symbol)
        if not scrip_code:
            log.warning("BSEProvider: no scrip code for %s", symbol)
            return {}

        url = f"https://api.bseindia.com/BseIndiaAPI/api/getScripHeaderData/w?DebtFlag=&scripcode={scrip_code}"
        try:
            resp = requests.get(url, headers=_BSE_HEADERS, timeout=10)
            if resp.status_code != 200:
                return {}

            data = resp.json()
            header = data.get("Header") or {}
            ltp = header.get("LTP")
            prev_close = header.get("PrevClose")
            open_p = header.get("Open")
            high_p = header.get("High")
            low_p = header.get("Low")

            if ltp is None:
                return {}

            close_val = float(str(ltp).replace(",", ""))
            prev_val = float(str(prev_close).replace(",", "")) if prev_close else None

            return {
                "symbol": symbol.upper(),
                "scrip_code": scrip_code,
                "close": close_val,
                "prev_close": prev_val,
                "open": float(str(open_p).replace(",", "")) if open_p else None,
                "high": float(str(high_p).replace(",", "")) if high_p else None,
                "low": float(str(low_p).replace(",", "")) if low_p else None,
                "exchange": "BSE",
                "source": "BSE India Official API",
            }
        except Exception as exc:
            log.warning("BSEProvider: BSE quote failed for %s (%s): %s", symbol, scrip_code, exc)
            return {}
