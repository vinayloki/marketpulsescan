"""
MarketPulse India — NSE Direct Provider (Primary)

Ticker universe: Direct from NSE's official CSV archives.
                 Fallback: PKScreener's daily-cached GitHub mirror.
                 Fallback 2: Last successful local cache.

OHLCV data:     yfinance batch downloads (full OHLCV, not just Close).
Fundamentals:   yfinance .info (parallel, ThreadPoolExecutor).

This is the zero-cost, zero-dependency primary provider.
"""

import io
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

from config.settings import (
    BATCH_DELAY_SECONDS,
    BATCH_SIZE,
    FUNDAMENTALS_WORKERS,
    MIN_DATA_POINTS,
    NSE_EQUITY_CSV_URL,
    NSE_EQUITY_MIRROR_URL,
    NSE_SYMBOLS_CACHE,
)
from config.sector_map import normalize_sector
from data_providers.base_provider import BaseDataProvider

log = logging.getLogger("marketpulse.provider")

# Request headers that mimic a browser — NSE rejects bare Python requests
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
}


class NSEDirectProvider(BaseDataProvider):
    """
    Primary data provider for MarketPulse India.

    Ticker universe fallback chain:
        1. archives.nseindia.com/content/equities/EQUITY_L.csv  (live NSE)
        2. pkjmesra/PKScreener GitHub mirror                    (very reliable)
        3. nse_symbols.json on disk                             (last success)

    OHLCV: yfinance batch download, full OHLCV MultiIndex DataFrame.
    Fundamentals: yfinance .info, parallel with ThreadPoolExecutor.
    """

    def __init__(self, fallback: Optional[BaseDataProvider] = None):
        self._fallback = fallback

    # ═══════════════════════════════════════════════════════════════
    #  TICKER UNIVERSE
    # ═══════════════════════════════════════════════════════════════

    def fetch_ticker_universe(self) -> list[str]:
        """Fetch all NSE equity tickers — three-level fallback chain."""
        tickers = self._fetch_from_nse_csv(NSE_EQUITY_CSV_URL, "NSE Live")
        if tickers:
            self._save_cache(tickers)
            return tickers

        log.warning("⚠️  NSE live CSV failed — trying GitHub mirror...")
        tickers = self._fetch_from_nse_csv(NSE_EQUITY_MIRROR_URL, "GitHub Mirror")
        if tickers:
            self._save_cache(tickers)
            return tickers

        log.warning("⚠️  GitHub mirror failed — loading disk cache...")
        tickers = self._load_cache()
        if tickers:
            log.info(f"   📂 Loaded {len(tickers)} tickers from cache")
            return tickers

        # All three failed — try fallback provider
        if self._fallback:
            log.warning("⚠️  All NSE sources failed — delegating to fallback provider")
            return self._fallback.fetch_ticker_universe()

        log.error("❌ All ticker sources failed. Returning empty list.")
        return []

    def _fetch_from_nse_csv(self, url: str, label: str) -> list[str]:
        """
        Download NSE's EQUITY_L.csv and extract valid equity symbols.

        The CSV format:
            SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, ...
        Only 'EQ' series are regular equities (exclude BE, BZ, SM, etc.)
        """
        try:
            log.info(f"   📡 Fetching ticker universe from {label}...")
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            resp.raise_for_status()

            df = pd.read_csv(io.StringIO(resp.text))
            df.columns = [c.strip().upper() for c in df.columns]

            # EQUITY_L.csv columns: SYMBOL, NAME OF COMPANY, SERIES, ...
            if "SYMBOL" not in df.columns:
                log.warning(f"   ⚠️  Unexpected CSV format from {label}")
                return []

            # Filter to EQ series only (regular cash-market equities)
            if " SERIES" in df.columns:
                df = df[df[" SERIES"].str.strip() == "EQ"]
            elif "SERIES" in df.columns:
                df = df[df["SERIES"].str.strip() == "EQ"]

            tickers = (
                df["SYMBOL"]
                .dropna()
                .str.strip()
                .str.upper()
                .unique()
                .tolist()
            )
            tickers = sorted([t for t in tickers if t and not t.isdigit()])
            log.info(f"   ✅ {len(tickers)} equity tickers from {label}")
            return tickers

        except Exception as e:
            log.warning(f"   ⚠️  {label} fetch failed: {e}")
            return []

    def _save_cache(self, tickers: list[str]) -> None:
        """Write tickers to disk cache for next-run fallback."""
        try:
            with open(NSE_SYMBOLS_CACHE, "w", encoding="utf-8") as f:
                json.dump(tickers, f)
        except Exception as e:
            log.warning(f"   ⚠️  Could not write ticker cache: {e}")

    def _load_cache(self) -> list[str]:
        """Read tickers from disk cache."""
        try:
            if NSE_SYMBOLS_CACHE.exists():
                with open(NSE_SYMBOLS_CACHE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return []

    # ═══════════════════════════════════════════════════════════════
    #  OHLCV DATA
    # ═══════════════════════════════════════════════════════════════

    def fetch_ohlcv(
        self,
        tickers: list[str],
        period: str = "13mo",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """
        Download full OHLCV for all tickers via yfinance.

        Returns a MultiIndex DataFrame: columns = (field, ticker)
        Fields: Open, High, Low, Close, Volume

        Downloads in batches of BATCH_SIZE to respect rate limits.
        Individual batch failures are skipped silently.
        """
        log.info(
            f"📡 Downloading {period} OHLCV for {len(tickers)} stocks "
            f"({interval} interval)..."
        )

        yf_tickers = [f"{t}.NS" for t in tickers]
        all_data = pd.DataFrame()
        total_batches = (len(yf_tickers) + BATCH_SIZE - 1) // BATCH_SIZE

        for i in range(0, len(yf_tickers), BATCH_SIZE):
            batch = yf_tickers[i : i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1

            log.info(
                f"   📦 Batch {batch_num}/{total_batches} "
                f"— {len(batch)} stocks..."
            )

            try:
                raw = yf.download(
                    tickers=batch,
                    period=period,
                    interval=interval,
                    group_by="ticker",
                    auto_adjust=True,
                    threads=True,
                    progress=False,
                )

                if raw.empty:
                    continue

                # yfinance returns multi-level when >1 ticker, flat when =1
                if len(batch) == 1:
                    sym = batch[0].replace(".NS", "")
                    raw.columns = pd.MultiIndex.from_tuples(
                        [(col, sym) for col in raw.columns]
                    )
                else:
                    # Swap levels: (ticker, field) → (field, ticker)
                    raw = raw.swaplevel(axis=1)
                    # Strip .NS from ticker level
                    raw.columns = pd.MultiIndex.from_tuples(
                        [(field, sym.replace(".NS", ""))
                         for field, sym in raw.columns]
                    )
                raw.sort_index(axis=1, inplace=True)

                all_data = raw if all_data.empty else all_data.join(
                    raw, how="outer"
                )

            except Exception as e:
                log.warning(f"   ⚠️  Batch {batch_num} failed: {e}")

            if batch_num < total_batches:
                time.sleep(BATCH_DELAY_SECONDS)

        if all_data.empty:
            log.error("❌ No OHLCV data downloaded at all!")
            if self._fallback:
                log.warning("   🔄 Delegating to fallback provider...")
                return self._fallback.fetch_ohlcv(tickers, period, interval)
            return pd.DataFrame()

        # Drop tickers with insufficient data (check Close column)
        if "Close" in all_data.columns.get_level_values(0):
            close = all_data["Close"]
            valid = [c for c in close.columns
                     if close[c].dropna().shape[0] >= MIN_DATA_POINTS]
            # Keep only valid tickers across all fields
            all_data = all_data.loc[
                :,
                all_data.columns.get_level_values(1).isin(valid)
            ]

        all_data.sort_index(inplace=True)
        valid_count = len(all_data.columns.get_level_values(1).unique())
        log.info(
            f"   ✅ OHLCV ready: {valid_count} stocks × "
            f"{len(all_data)} trading days"
        )
        return all_data

    # ═══════════════════════════════════════════════════════════════
    #  FUNDAMENTALS
    # ═══════════════════════════════════════════════════════════════

    def fetch_fundamentals(self, tickers: list[str]) -> dict[str, dict]:
        """
        Fetch fundamental data for each ticker via yfinance .info.
        Uses ThreadPoolExecutor for parallel fetching.
        """
        log.info(f"🔬 Fetching fundamentals for {len(tickers)} stocks...")
        results: dict[str, dict] = {}

        with ThreadPoolExecutor(max_workers=FUNDAMENTALS_WORKERS) as ex:
            future_map = {
                ex.submit(self._fetch_single_fundamental, t): t
                for t in tickers
            }
            done = 0
            for future in as_completed(future_map):
                ticker = future_map[future]
                done += 1
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    log.debug(f"   fundamentals failed {ticker}: {e}")
                    results[ticker] = {"s": ticker}
                if done % 25 == 0:
                    log.info(f"   📦 Fundamentals: {done}/{len(tickers)} done")

        valid = sum(1 for v in results.values() if v.get("pe") or v.get("mcap"))
        log.info(f"   ✅ Fundamentals: {valid}/{len(results)} with data")
        return results

    def _fetch_single_fundamental(self, symbol: str) -> dict:
        """Fetch and normalise fundamental info for one stock."""
        try:
            info = yf.Ticker(f"{symbol}.NS").info
            mcap = info.get("marketCap")
            return {
                "s":      symbol,
                "name":   info.get("shortName") or info.get("longName") or symbol,
                "sector": normalize_sector(info.get("sector")),
                "ind":    info.get("industry"),
                "mcap":   round(mcap / 1e7, 1) if mcap else None,  # → ₹ Cr
                "pe":     round(info["trailingPE"], 1)
                          if info.get("trailingPE") else None,
                "eps":    round(info["trailingEps"], 2)
                          if info.get("trailingEps") else None,
                "52h":    round(info["fiftyTwoWeekHigh"], 2)
                          if info.get("fiftyTwoWeekHigh") else None,
                "52l":    round(info["fiftyTwoWeekLow"], 2)
                          if info.get("fiftyTwoWeekLow") else None,
                "bv":     round(info["bookValue"], 2)
                          if info.get("bookValue") else None,
                "dy":     round(info.get("dividendYield", 0) * 100, 2)
                          if info.get("dividendYield") else None,
            }
        except Exception as e:
            log.debug(f"   fundamentals error {symbol}: {e}")
            return {"s": symbol}

    # ═══════════════════════════════════════════════════════════════
    #  MARKET CAP CATEGORISATION
    # ═══════════════════════════════════════════════════════════════

    def fetch_mcap_categories(self) -> dict[str, str]:
        """
        Fetch NIFTY 100 and NIFTY MIDCAP 150 indices to map tickers to
        Large (L) and Mid (M) cap arrays. Default is Small (S).
        Returns: Dict mapping ticker to 'L', 'M' or 'S'.
        """
        log.info("📊 Fetching NSE indices for Market Cap classification...")
        mcap_map = {}
        
        # 1. Large Caps (Nifty 100)
        url_100 = "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
        try:
            r = requests.get(url_100, headers=_HEADERS, timeout=10)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            for t in df["Symbol"].dropna().unique():
                mcap_map[str(t).strip().upper()] = "L"
        except Exception as e:
            log.warning(f"   ⚠️ Could not fetch Nifty 100: {e}")

        # 2. Mid Caps (Nifty Midcap 150)
        url_150 = "https://archives.nseindia.com/content/indices/ind_niftymidcap150list.csv"
        try:
            r = requests.get(url_150, headers=_HEADERS, timeout=10)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            for t in df["Symbol"].dropna().unique():
                mcap_map[str(t).strip().upper()] = "M"
        except Exception as e:
            log.warning(f"   ⚠️ Could not fetch Nifty 150: {e}")

        log.info(f"   ✅ Market Cap mapping complete: {list(mcap_map.values()).count('L')} Large, {list(mcap_map.values()).count('M')} Mid")
        return mcap_map
