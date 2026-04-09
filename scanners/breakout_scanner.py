"""
MarketPulse India — 52-Week High Breakout Scanner

Signal: Stock is trading within BREAKOUT_PROXIMITY_PCT of its 52-week high
        AND today's volume is >= BREAKOUT_VOLUME_MULT × 20-day average volume.

Scoring (max 30 pts):
    - Base: 20 pts for proximity trigger
    - Volume quality bonus: up to 10 pts (scales with volume ratio)
    - Exact 52W high touch: +5 pts (capped at 30 total)
"""

import logging
import pandas as pd

from config.settings import (
    BREAKOUT_PROXIMITY_PCT,
    BREAKOUT_VOLUME_MULT,
)
from engine.opportunity_model import ScanResult
from scanners.base_scanner import BaseScanner

log = logging.getLogger("marketpulse.breakout")


class BreakoutScanner(BaseScanner):
    NAME = "52W_BREAKOUT"
    MAX_SCORE = 30

    def scan(self, ohlcv: pd.DataFrame) -> dict[str, ScanResult]:
        """
        Scan for 52-week high breakout candidates.

        Conditions:
            1. Close ≥ (1 - BREAKOUT_PROXIMITY_PCT/100) × 52W High
            2. Today's Volume ≥ BREAKOUT_VOLUME_MULT × 20D avg Volume
        """
        results: dict[str, ScanResult] = {}

        if "Close" not in ohlcv.columns.get_level_values(0):
            log.warning("⚠️  BreakoutScanner: No 'Close' column in OHLCV")
            return results
        if "High" not in ohlcv.columns.get_level_values(0):
            log.warning("⚠️  BreakoutScanner: No 'High' column in OHLCV")
            return results
        if "Volume" not in ohlcv.columns.get_level_values(0):
            log.warning("⚠️  BreakoutScanner: No 'Volume' column in OHLCV")
            return results

        close_df  = ohlcv["Close"]
        high_df   = ohlcv["High"]
        volume_df = ohlcv["Volume"]

        tickers = close_df.columns.tolist()
        triggered_count = 0

        for ticker in tickers:
            try:
                close  = close_df[ticker].dropna()
                high   = high_df[ticker].dropna()
                volume = volume_df[ticker].dropna()

                if len(close) < 50 or len(volume) < 20:
                    continue

                # ── Core values ───────────────────────────────────────
                current_close  = float(close.iloc[-1])
                high_52w       = float(high.tail(252).max())
                vol_today      = float(volume.iloc[-1])
                vol_20d_avg    = float(self._vol_sma(volume, 20).iloc[-1])

                if high_52w <= 0 or vol_20d_avg <= 0:
                    continue

                # ── Conditions ────────────────────────────────────────
                proximity_ratio = current_close / high_52w
                pct_from_high   = (1 - proximity_ratio) * 100
                vol_ratio       = vol_today / vol_20d_avg

                near_52w_high   = pct_from_high <= BREAKOUT_PROXIMITY_PCT
                volume_confirms = vol_ratio >= BREAKOUT_VOLUME_MULT

                if not (near_52w_high and volume_confirms):
                    continue

                # ── Scoring ───────────────────────────────────────────
                # Base 20 pts for proximity trigger
                score = 20

                # Volume quality bonus (0–10 pts, linear up to 3×)
                vol_bonus = min(10, int((vol_ratio - BREAKOUT_VOLUME_MULT) / 1.5 * 10))
                score += vol_bonus

                # Touching exact 52W high: +5 pts
                if pct_from_high <= 0.5:
                    score += 5

                score = min(score, self.MAX_SCORE)

                signals = ["52W_BREAKOUT"]
                if vol_ratio >= 3.0:
                    signals.append("HIGH_VOLUME")

                results[ticker] = ScanResult(
                    ticker=ticker,
                    scanner=self.NAME,
                    triggered=True,
                    score=score,
                    signals=signals,
                    indicators={
                        "high_52w":         round(high_52w, 2),
                        "pct_from_52w_high": round(pct_from_high, 2),
                        "volume_ratio":     round(vol_ratio, 2),
                        "price":            round(current_close, 2),
                    },
                )
                triggered_count += 1

            except Exception as e:
                log.debug(f"   BreakoutScanner skip {ticker}: {e}")
                continue

        log.info(f"   📈 BreakoutScanner: {triggered_count} signals found")
        return results
