"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — Market Regime Filter                                   ║
║                                                                              ║
║  Classifies market conditions using NIFTY 50 vs EMA200.                     ║
║                                                                              ║
║  Bull     → NIFTY > EMA200 by more than REGIME_SIDEWAYS_BAND_PCT %          ║
║  Sideways → NIFTY within ±REGIME_SIDEWAYS_BAND_PCT % of EMA200              ║
║  Bear     → NIFTY < EMA200 by more than REGIME_SIDEWAYS_BAND_PCT %          ║
║                                                                              ║
║  Public API:                                                                 ║
║    rf = RegimeFilter()                                                       ║
║    rf.get_current_regime()              → ('Bull', 1.0)                      ║
║    rf.get_regime_on_date(date)          → ('Sideways', 0.5)                  ║
║    rf.get_regime_series()               → pd.Series[str]                     ║
║    rf.get_nifty_close()                 → pd.Series[float]                   ║
║    rf.get_nifty_vs_ema200()             → pd.Series[float] (% deviation)     ║
║                                                                              ║
║  Data: yfinance download of ^NSEI (~13 months). Cached as parquet.          ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import sys
import time
from pathlib import Path
from typing import Optional, Union

import pandas as pd
import yfinance as yf

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config.settings import (
    CACHE_DIR,
    NIFTY_SYMBOL,
    OUTPUT_DIR,
    REGIME_BEAR_SIZE_MULT,
    REGIME_BULL_SIZE_MULT,
    REGIME_EMA_PERIOD,
    REGIME_SIDEWAYS_BAND_PCT,
    REGIME_SIDEWAYS_SIZE_MULT,
)

log = logging.getLogger("regime_filter")

# Cache path for NIFTY data
NIFTY_CACHE = CACHE_DIR / "nifty_cache.parquet"
NIFTY_CACHE_MAX_AGE_H = 4   # refresh intraday


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

    No-lookahead guarantee: EMA200 at date T uses only data up to T because
    pandas ewm() is computed left-to-right (it is inherently causal).
    """

    def __init__(self, force_download: bool = False):
        self._close: Optional[pd.Series]  = None
        self._ema200: Optional[pd.Series] = None
        self._regime_series: Optional[pd.Series] = None
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
                    log.info(f"  NIFTY loaded from cache ({age_h:.1f}h old, {len(self._close)} days)")
                    self._build_indicators()
                    return
                except Exception as exc:
                    log.warning(f"  NIFTY cache load failed ({exc}) — re-downloading")

        self._download()

    def _download(self) -> None:
        """Download NIFTY 50 from yfinance."""
        log.info(f"  Downloading NIFTY 50 ({NIFTY_SYMBOL})...")
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
            log.info(f"  NIFTY downloaded: {len(self._close)} trading days")

            # Cache
            raw[["Close"]].to_parquet(NIFTY_CACHE)
            self._build_indicators()

        except Exception as exc:
            log.warning(f"  NIFTY download failed: {exc} — regime will default to Bull")
            self._close     = pd.Series(dtype=float)
            self._ema200    = pd.Series(dtype=float)
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
        label = self._regime_series.iloc[-1]
        mult  = _classify(self._get_pct_vs_ema200_latest())[1]
        return label, mult

    def get_regime_on_date(
        self,
        date: Union[str, pd.Timestamp],
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

        ema200_on_date = float(
            past_close.ewm(span=REGIME_EMA_PERIOD, adjust=False).mean().iloc[-1]
        )
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
        if self._close is None or self._ema200 is None:
            return pd.Series(dtype=float)
        return (self._close - self._ema200) / self._ema200 * 100

    def save_regime_json(self) -> Path:
        """Save current regime state to scan_results/market_regime.json."""
        regime, mult = self.get_current_regime()
        nifty_val = float(self._close.iloc[-1]) if self._close is not None and not self._close.empty else 0
        ema200_val = float(self._ema200.iloc[-1]) if self._ema200 is not None and not self._ema200.empty else 0
        pct = (nifty_val - ema200_val) / ema200_val * 100 if ema200_val else 0

        # Regime stats (last 52 weeks)
        breakdown = {}
        if self._regime_series is not None and not self._regime_series.empty:
            tail = self._regime_series.tail(252)
            for r in ["Bull", "Sideways", "Bear"]:
                count = (tail == r).sum()
                breakdown[r] = {
                    "days":    int(count),
                    "pct_of_year": round(count / len(tail) * 100, 1),
                }

        output = {
            "generated":        pd.Timestamp.now().strftime("%d %b %Y %H:%M"),
            "regime":           regime,
            "size_multiplier":  mult,
            "nifty_close":      round(nifty_val, 2),
            "ema_200":          round(ema200_val, 2),
            "pct_vs_ema200":    round(pct, 2),
            "last_date":        str(self._close.index[-1].date()) if self._close is not None and not self._close.empty else "",
            "regime_breakdown_52w": breakdown,
            "interpretation": {
                "Bull":     "NIFTY above EMA200 — favor breakout/momentum strategies",
                "Sideways": "NIFTY near EMA200 — be selective, only high-score setups",
                "Bear":     "NIFTY below EMA200 — avoid longs; highest confidence only",
            }.get(regime, ""),
        }

        out_path = OUTPUT_DIR / "market_regime.json"
        import json
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(output, fh, indent=2, ensure_ascii=False)

        log.info(f"  Market regime saved: {out_path.name}")
        return out_path

    def _get_pct_vs_ema200_latest(self) -> float:
        if self._close is None or self._ema200 is None or self._close.empty:
            return 5.0
        c = float(self._close.iloc[-1])
        e = float(self._ema200.iloc[-1])
        return (c - e) / e * 100 if e else 5.0


# ══════════════════════════════════════════════════════════════════════════════
#  CLI  — run standalone: python regime_filter.py
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    print("\nMarketPulse India - Market Regime Filter\n")

    rf = RegimeFilter()
    regime, mult = rf.get_current_regime()
    nifty  = rf.get_nifty_close()
    pct_ser = rf.get_nifty_vs_ema200()

    if not nifty.empty:
        print(f"  NIFTY 50     : {nifty.iloc[-1]:>9,.2f}")
        print(f"  EMA-200      : {nifty.iloc[-1] - (pct_ser.iloc[-1]/100 * nifty.iloc[-1] / (1 + pct_ser.iloc[-1]/100)):>9,.2f}")
        print(f"  vs EMA200    : {pct_ser.iloc[-1]:>+8.2f}%")

    regime_icon = {"Bull": "BULL", "Sideways": "SIDEWAYS", "Bear": "BEAR"}.get(regime, regime)
    print(f"  Regime       : {regime_icon}")
    print(f"  Size mult    : {mult}x")

    # Show last 4-week history
    tail = rf.get_regime_series().tail(20)
    if not tail.empty:
        print(f"\n  Last 20 days: {', '.join(tail.tolist())}")

    path = rf.save_regime_json()
    print(f"\n  Saved: {path}\n")


if __name__ == "__main__":
    main()
