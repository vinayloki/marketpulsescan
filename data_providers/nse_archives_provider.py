"""
MarketPulse India — NSE Archives Provider (Bhavcopy + Symbols)

Uses the `nse-archives` library to fetch:
1. Daily Bhavcopy (high-speed OHLCV for current day)
2. NSE Equity ticker universe (directly from exchange archives)
"""

import logging
from typing import Optional
import pandas as pd
from datetime import datetime, timedelta

from data_providers.base_provider import BaseDataProvider

try:
    from nsedata import nse
except ImportError:
    nse = None

log = logging.getLogger("marketpulse.provider")

class NseArchivesProvider(BaseDataProvider):
    """
    Provider utilizing the 'nse-archives' (imported as nsedata) package.
    Optimized for GitHub Actions / cloud runners where direct requests to NSE get blocked.
    """

    def __init__(self, fallback: Optional[BaseDataProvider] = None):
        self._fallback = fallback
        if nse is None:
            log.warning("⚠️  nse-archives package not installed! NseArchivesProvider will fail.")
            self.api = None
        else:
            self.api = nse


    def fetch_ticker_universe(self) -> list[str]:
        """Fetch all NSE equity tickers using the latest available Bhavcopy."""
        if not self.api:
            return self._fallback.fetch_ticker_universe() if self._fallback else []

        try:
            log.info("📡 Fetching ticker universe via nse-archives...")
            # We need the most recent Bhavcopy to extract valid active tickers.
            # Look back up to 5 days to find the latest trading day.
            df = None
            for i in range(6):
                dt = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                try:
                    df = self.api.get("capital_market", "equities_sme", "sec_bhavdata_full", dt)
                    if df is not None and not df.empty:
                        break
                except Exception:
                    continue

            if df is not None and not df.empty:
                # Column is typically 'SYMBOL'
                sym_col = next((c for c in df.columns if c.upper() in ["SYMBOL", "TKT_NAME", "INSTRUMENT"]), None)
                srs_col = next((c for c in df.columns if c.upper() in ["SERIES", "SCTYSRS"]), None)
                
                if sym_col:
                    # Filter for only regular equities (SERIES == 'EQ' or similar)
                    if srs_col:
                        df = df[df[srs_col].astype(str).str.strip().str.upper() == "EQ"]

                    tickers = df[sym_col].dropna().astype(str).str.strip().str.upper().unique().tolist()
                    tickers = sorted([t for t in tickers if t and not t.isdigit() and "NIFTY" not in t])
                    log.info(f"   ✅ {len(tickers)} equity tickers from nse-archives")
                    return tickers
            
            log.warning("⚠️  nse-archives returned empty or unrecognized dataframe.")
        except Exception as e:
            log.warning(f"⚠️  nse-archives ticker fetch failed: {e}")

        # Fallback
        if self._fallback:
            log.info("   ↳ Delegating to fallback provider")
            return self._fallback.fetch_ticker_universe()
        
        return []

    def fetch_daily_bhavcopy(self, date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Download a single day's Bhavcopy as a DataFrame.
        Looks back up to 5 days to find the most recent trading day if date not provided.
        Returns empty DataFrame if failed.
        """
        if not self.api:
            return pd.DataFrame()

        try:
            log.info(f"📡 Fetching Bhavcopy for {date.strftime('%Y-%m-%d') if date else 'latest'} via nse-archives...")
            
            df = None
            if date:
                df = self.api.get("capital_market", "equities_sme", "sec_bhavdata_full", date.strftime("%Y-%m-%d"))
            else:
                for i in range(6):
                    dt = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                    try:
                        df = self.api.get("capital_market", "equities_sme", "sec_bhavdata_full", dt)
                        if df is not None and not df.empty:
                            break
                    except Exception:
                        continue
            
            if df is not None and not df.empty:
                # Filter 'EQ' series only so we don't patch options or bonds
                srs_col = next((c for c in df.columns if c.upper() in ["SERIES", "SCTYSRS"]), None)
                if srs_col:
                    df = df[df[srs_col].astype(str).str.strip().str.upper() == "EQ"]
                
                log.info(f"   ✅ Fetched {len(df)} rows from Bhavcopy")
                return df
            log.warning("⚠️  Bhavcopy returned empty.")
        except Exception as e:
            log.warning(f"⚠️  Bhavcopy fetch failed: {e}")
            
        return pd.DataFrame()

    def fetch_ohlcv(self, tickers: list[str], period: str = "13mo", interval: str = "1d") -> pd.DataFrame:
        """
        We DO NOT use Bhavcopy for full historical OHLCV. Bhavcopy is unadjusted.
        We delegate full history to the fallback provider (e.g., yfinance).
        """
        if self._fallback:
            return self._fallback.fetch_ohlcv(tickers, period, interval)
        return pd.DataFrame()

    def fetch_fundamentals(self, tickers: list[str]) -> dict[str, dict]:
        """Delegate fundamentals to fallback provider."""
        if self._fallback:
            return self._fallback.fetch_fundamentals(tickers)
        return {}

