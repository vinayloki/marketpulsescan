"""
MarketPulse — Market Regime Filter

Classifies market conditions using NIFTY 50 vs EMA200.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

from marketpulse.config.settings import (
    CACHE_DIR,
    NIFTY_SYMBOL,
    OUTPUT_DIR,
    REGIME_BEAR_SIZE_MULT,
    REGIME_BULL_SIZE_MULT,
    REGIME_EMA_PERIOD,
    REGIME_SIDEWAYS_BAND_PCT,
    REGIME_SIDEWAYS_SIZE_MULT,
)

log = logging.getLogger(__name__)

# Cache path for NIFTY data
NIFTY_CACHE = CACHE_DIR / "nifty_cache.parquet"
NIFTY_CACHE_MAX_AGE_H = 4.0  # refresh intraday


def _classify(pct_vs_ema: float) -> tuple[str, float]:
    """
    Map percentage deviation from EMA200 to (regime_label, size_multiplier).
    pct_vs_ema > 0  → NIFTY is ABOVE EMA200
    pct_vs_ema < 0  → NIFTY is BELOW EMA200
    """
    if pct_vs_ema > REGIME_SIDEWAYS_BAND_PCT:
        return "Bull", REGIME_BULL_SIZE_MULT
    elif pct_vs_ema < -REGIME_SIDEWAYS_BAND_PCT:
        return "Bear", REGIME_BEAR_SIZE_MULT
    else:
        return "Sideways", REGIME_SIDEWAYS_SIZE_MULT


class RegimeFilter:
    """
    Downloads NIFTY 50 history, computes EMA200, and classifies each date.

    No-lookahead guarantee: EMA200 at date T uses only data up to T.
    """

    def __init__(self, force_download: bool = False) -> None:
        self._close: pd.Series = pd.Series(dtype=float)
        self._ema200: pd.Series = pd.Series(dtype=float)
        self._regime_series: pd.Series = pd.Series(dtype=str)
        self._load(force_download)

    # ── Data loading ─────────────────────────────────────────────────────

    def _load(self, force: bool) -> None:
        """Load NIFTY close prices (cache → yfinance)."""
        if not force and NIFTY_CACHE.exists():
            age_h = (time.time() - NIFTY_CACHE.stat().st_mtime) / 3600
            if age_h < NIFTY_CACHE_MAX_AGE_H:
                try:
                    df = pd.read_parquet(NIFTY_CACHE)
                    self._close = df["Close"]
                    log.info(
                        "NIFTY loaded from cache (%.1fh old, %d days)", age_h, len(self._close)
                    )
                    self._build_indicators()
                    return
                except Exception as exc:
                    log.warning("NIFTY cache load failed (%s) — re-downloading", exc)

        self._download()

    def _download(self) -> None:
        """Download NIFTY 50 from yfinance."""
        log.info("Downloading NIFTY 50 (%s)...", NIFTY_SYMBOL)
        try:
            raw = yf.download(
                NIFTY_SYMBOL,
                period="13mo",
                interval="1d",
                auto_adjust=True,
                progress=False,
            )
            if raw.empty:
                raise ValueError("Empty download")

            # Flatten multi-level columns if returned
            if isinstance(raw.columns, pd.MultiIndex):
                raw.columns = raw.columns.get_level_values(0)

            self._close = raw["Close"].dropna()
            log.info("NIFTY downloaded: %d trading days", len(self._close))

            # Cache
            raw[["Close"]].to_parquet(NIFTY_CACHE)
            self._build_indicators()

        except Exception as exc:
            log.warning("NIFTY download failed: %s — regime will default to Bull", exc)
            self._close = pd.Series(dtype=float)
            self._ema200 = pd.Series(dtype=float)
            self._regime_series = pd.Series(dtype=str)

    def _build_indicators(self) -> None:
        """Compute EMA200 and classify every date."""
        if self._close is None or self._close.empty:
            self._ema200 = pd.Series(dtype=float)
            self._regime_series = pd.Series(dtype=str)
            return

        self._ema200 = self._close.ewm(span=REGIME_EMA_PERIOD, adjust=False).mean()

        pct = (self._close - self._ema200) / self._ema200 * 100
        self._regime_series = pct.apply(lambda x: _classify(x)[0])

    # ── Public API ──────────────────────────────────────────────────────

    def get_current_regime(self) -> tuple[str, float]:
        """Returns (regime, size_multiplier) as of the latest available date."""
        if self._regime_series is None or self._regime_series.empty:
            return "Bull", REGIME_BULL_SIZE_MULT
        label = str(self._regime_series.iloc[-1])
        mult = _classify(self._get_pct_vs_ema200_latest())[1]
        return label, mult

    def get_regime_on_date(
        self,
        date: str | pd.Timestamp,
    ) -> tuple[str, float]:
        """
        Returns (regime, size_multiplier) on a specific historical date.
        Strict no-lookahead: uses only data up to and including `date`.
        """
        if self._close is None or self._close.empty:
            return "Bull", REGIME_BULL_SIZE_MULT

        ts = pd.Timestamp(date)
        past_close = self._close.loc[self._close.index <= ts]

        if past_close.empty:
            return "Bull", REGIME_BULL_SIZE_MULT

        ema200_on_date = float(past_close.ewm(span=REGIME_EMA_PERIOD, adjust=False).mean().iloc[-1])
        current = float(past_close.iloc[-1])
        pct = (current - ema200_on_date) / ema200_on_date * 100
        return _classify(pct)

    def get_regime_series(self) -> pd.Series:
        """Full daily regime series (string labels)."""
        return self._regime_series if self._regime_series is not None else pd.Series(dtype=str)

    def get_nifty_close(self) -> pd.Series:
        """Full NIFTY close price series."""
        return self._close if self._close is not None else pd.Series(dtype=float)

    def get_nifty_vs_ema200(self) -> pd.Series:
        """% deviation of NIFTY from EMA200 at each date."""
        if self._close is None or self._ema200 is None or self._close.empty or self._ema200.empty:
            return pd.Series(dtype=float)
        return (self._close - self._ema200) / self._ema200 * 100

    def save_regime_json(self) -> Path:
        """Save current regime state to scan_results/market_regime.json."""
        regime, mult = self.get_current_regime()
        nifty_val = (
            float(self._close.iloc[-1])
            if self._close is not None and not self._close.empty
            else 0.0
        )
        ema200_val = (
            float(self._ema200.iloc[-1])
            if self._ema200 is not None and not self._ema200.empty
            else 0.0
        )
        pct = (nifty_val - ema200_val) / ema200_val * 100 if ema200_val else 0.0

        # Regime stats (last 52 weeks)
        breakdown = {}
        if self._regime_series is not None and not self._regime_series.empty:
            tail = self._regime_series.tail(252)
            for r in ["Bull", "Sideways", "Bear"]:
                count = int((tail == r).sum())
                breakdown[r] = {
                    "days": count,
                    "pct_of_year": round(count / len(tail) * 100, 1) if len(tail) > 0 else 0.0,
                }

        output = {
            "generated": datetime.now().strftime("%d %b %Y %H:%M"),
            "regime": regime,
            "size_multiplier": mult,
            "nifty_close": round(nifty_val, 2),
            "ema_200": round(ema200_val, 2),
            "pct_vs_ema200": round(pct, 2),
            "last_date": str(self._close.index[-1].date())
            if self._close is not None and not self._close.empty
            else "",
            "regime_breakdown_52w": breakdown,
            "interpretation": {
                "Bull": "NIFTY above EMA200 — favor breakout/momentum strategies",
                "Sideways": "NIFTY near EMA200 — be selective, only high-score setups",
                "Bear": "NIFTY below EMA200 — avoid longs; highest confidence only",
            }.get(regime, ""),
        }

        out_path = OUTPUT_DIR / "market_regime.json"
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2, ensure_ascii=False)

        log.info("Market regime saved: %s", out_path.name)
        return out_path

    def _get_pct_vs_ema200_latest(self) -> float:
        if self._close is None or self._ema200 is None or self._close.empty or self._ema200.empty:
            return 5.0
        c = float(self._close.iloc[-1])
        e = float(self._ema200.iloc[-1])
        return (c - e) / e * 100 if e else 5.0
