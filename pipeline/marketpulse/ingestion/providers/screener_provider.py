"""
Screener Provider — scrapes company metrics and live stock prices from Screener.in.

Scrapes: https://www.screener.in/company/{symbol}/
Extracts:
  - name: Company Name
  - close: Current Price (INR)
  - mcap_cr: Market Capitalization (Cr)
  - high_52w / low_52w: 52-Week High and Low
  - pe_ratio: Stock P/E
  - book_value: Book Value
  - roce: Return on Capital Employed (%)
  - roe: Return on Equity (%)

Never raises from fetch_* methods — logs and returns empty dict on failure.
"""

from __future__ import annotations

import re
import logging
from typing import Any

import requests
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class ScreenerProvider:
    """Scraper provider for Screener.in company data."""

    capabilities: frozenset[str] = frozenset({"screener_quote", "fundamentals"})

    def fetch_screener_quote(self, symbol: str) -> dict[str, Any]:
        """
        Fetch company quote and key metrics from Screener.in for a symbol.
        Returns dict with parsed values or empty dict on error.
        """
        clean_sym = symbol.strip().upper()
        url = f"https://www.screener.in/company/{clean_sym}/"

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=6)
            if resp.status_code != 200:
                log.debug("ScreenerProvider: HTTP %d for %s", resp.status_code, clean_sym)
                return {}

            soup = BeautifulSoup(resp.text, "html.parser")
            out: dict[str, Any] = {"symbol": clean_sym, "source": "Screener.in"}

            # Extract Company Name
            h1 = soup.find("h1")
            if h1:
                out["name"] = h1.text.strip()

            # Parse Top Ratios list
            top_ratios = soup.find("ul", {"id": "top-ratios"})
            if top_ratios:
                for li in top_ratios.find_all("li"):
                    name_span = li.find("span", {"class": "name"})
                    num_span = li.find("span", {"class": "number"})
                    if name_span and num_span:
                        key = name_span.text.strip().lower()
                        raw_val = num_span.text.strip().replace(",", "")

                        try:
                            val = float(raw_val)
                        except ValueError:
                            val = raw_val

                        if "current price" in key:
                            out["close"] = val
                        elif "market cap" in key:
                            out["mcap_cr"] = val
                        elif "stock p/e" in key:
                            out["pe_ratio"] = val
                        elif "book value" in key:
                            out["book_value"] = val
                        elif "roce" in key:
                            out["roce"] = val
                        elif "roe" in key:
                            out["roe"] = val
                        elif "high / low" in key:
                            # High / Low split, e.g. "1,770 / 1,450"
                            parts = raw_val.split("/")
                            if len(parts) == 2:
                                try:
                                    out["high_52w"] = float(parts[0].strip().replace(",", ""))
                                    out["low_52w"] = float(parts[1].strip().replace(",", ""))
                                except ValueError:
                                    pass

            return out
        except Exception as exc:
            log.warning("ScreenerProvider: fetch failed for %s: %s", clean_sym, exc)
            return {}
