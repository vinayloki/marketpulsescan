"""
MarketPulse India — YFinance Fallback Provider

Pure yfinance implementation used when NSEDirectProvider
fails to fetch the ticker universe.

OHLCV: delegates fully to NSEDirectProvider's download logic
        (yfinance is already the underlying source, so this just
         provides an alternative universe-fetching strategy).
"""

import logging
import time

import pandas as pd
import yfinance as yf

from config.settings import BATCH_DELAY_SECONDS, BATCH_SIZE, MIN_DATA_POINTS
from data_providers.base_provider import BaseDataProvider

log = logging.getLogger("marketpulse.yf_provider")

# Seed list of large/liquid NSE indices used to infer the equity universe
# when NSE's CSV is unreachable. Not exhaustive — covers ~500 stocks.
_NIFTY_INDICES = [
    "^NSEI",        # Nifty 50
    "^NSEMDCP50",   # Nifty Midcap 50
]


class YFinanceProvider(BaseDataProvider):
    """
    Fallback provider using pure yfinance.

    Universe strategy: Downloads Nifty 50 components from Wikipedia
    (which yfinance can help with) then expands via known NSE index ETFs.

    NOTE: This will return a smaller universe (~200–500 stocks) compared
    to NSEDirectProvider (~2000+). Use only when NSE CSV is unreachable.
    """

    def fetch_ticker_universe(self) -> list[str]:
        """
        Attempt to build a symbol list from Wikipedia's Nifty 500 table.
        Returns up to ~500 well-known NSE tickers.
        """
        log.info("📡 [Fallback] Fetching ticker universe from Wikipedia tables...")
        tickers = set()

        urls = [
            "https://en.wikipedia.org/wiki/NIFTY_500",
            "https://en.wikipedia.org/wiki/NIFTY_100",
            "https://en.wikipedia.org/wiki/NIFTY_50",
        ]

        for url in urls:
            try:
                tables = pd.read_html(url)
                for table in tables:
                    cols = [str(c).upper() for c in table.columns]
                    # Look for a column containing "SYMBOL" or "TICKER"
                    sym_col = next(
                        (c for c in cols if "SYMBOL" in c or "TICKER" in c),
                        None,
                    )
                    if sym_col is None:
                        continue
                    idx = cols.index(sym_col)
                    syms = table.iloc[:, idx].dropna().str.strip().str.upper()
                    tickers.update(
                        [s for s in syms if s and not s.isdigit()]
                    )
                if len(tickers) > 100:
                    break
            except Exception as e:
                log.debug(f"   Wikipedia table parse failed for {url}: {e}")
                continue

        result = sorted(list(tickers))
        log.info(f"   ✅ [Fallback] {len(result)} tickers from Wikipedia")
        return result

    def fetch_ohlcv(
        self,
        tickers: list[str],
        period: str = "13mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Delegate to same yfinance batch logic as NSEDirectProvider."""
        # Import here to avoid circular dependency
        from data_providers.nse_direct_provider import NSEDirectProvider
        # Use NSEDirectProvider's download logic (no fallback set to avoid loop)
        return NSEDirectProvider(fallback=None).fetch_ohlcv(
            tickers, period, interval
        )

    def fetch_fundamentals(self, tickers: list[str]) -> dict[str, dict]:
        """Delegate to NSEDirectProvider's fundamentals logic."""
        from data_providers.nse_direct_provider import NSEDirectProvider
        return NSEDirectProvider(fallback=None).fetch_fundamentals(tickers)
