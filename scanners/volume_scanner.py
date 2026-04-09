"""
MarketPulse India — Volume Spike Scanner

Signal: Today's volume is >= VOLUME_SPIKE_MULT × 20-day average volume
        AND today's close > yesterday's close (bullish pressure confirmed).

Scoring (max 25 pts):
    - Score scales linearly with volume ratio from SPIKE_MULT to MAX_MULT.
    - Price direction bonus: +3 pts if close is also above 10-day SMA.
    - Capped at MAX_SCORE = 25.
"""

import logging
import pandas as pd

from config.settings import (
    VOLUME_SPIKE_MAX_MULT,
    VOLUME_SPIKE_MULT,
)
from engine.opportunity_model import ScanResult
from scanners.base_scanner import BaseScanner

log = logging.getLogger("marketpulse.volume")


class VolumeScanner(BaseScanner):
    NAME = "VOLUME_SPIKE"
    MAX_SCORE = 25

    def scan(self, ohlcv: pd.DataFrame) -> dict[str, ScanResult]:
        """
        Scan for unusual volume spikes with bullish price confirmation.

        Conditions:
            1. Volume today >= VOLUME_SPIKE_MULT × 20D avg volume
            2. Close today > Close yesterday (bullish direction)
        """
        results: dict[str, ScanResult] = {}

        required = {"Close", "Volume"}
        available = set(ohlcv.columns.get_level_values(0))
        if not required.issubset(available):
            log.warning(f"⚠️  VolumeScanner: Missing fields {required - available}")
            return results

        close_df  = ohlcv["Close"]
        volume_df = ohlcv["Volume"]
        triggered_count = 0

        for ticker in close_df.columns:
            try:
                close  = close_df[ticker].dropna()
                volume = volume_df[ticker].dropna()

                if len(close) < 21 or len(volume) < 21:
                    continue

                # ── Core values ───────────────────────────────────────
                close_today     = float(close.iloc[-1])
                close_yesterday = float(close.iloc[-2])
                vol_today       = float(volume.iloc[-1])
                vol_20d_avg     = float(self._vol_sma(volume, 20).iloc[-1])
                sma_10          = float(close.rolling(10).mean().iloc[-1])

                if vol_20d_avg <= 0:
                    continue

                vol_ratio = vol_today / vol_20d_avg

                # ── Conditions ────────────────────────────────────────
                volume_spikes  = vol_ratio >= VOLUME_SPIKE_MULT
                price_up       = close_today > close_yesterday

                if not (volume_spikes and price_up):
                    continue

                # ── Scoring ───────────────────────────────────────────
                # Linear scale: SPIKE_MULT → MAX_MULT maps to 0 → 22
                normalised = (vol_ratio - VOLUME_SPIKE_MULT) / (
                    VOLUME_SPIKE_MAX_MULT - VOLUME_SPIKE_MULT
                )
                score = int(min(22, normalised * 22))

                # Bonus: price above 10D SMA confirms trend
                if close_today > sma_10:
                    score += 3

                score = min(score, self.MAX_SCORE)

                pct_change = ((close_today - close_yesterday) / close_yesterday * 100)

                results[ticker] = ScanResult(
                    ticker=ticker,
                    scanner=self.NAME,
                    triggered=True,
                    score=score,
                    signals=["VOLUME_SPIKE"],
                    indicators={
                        "volume_ratio": round(vol_ratio, 2),
                        "price":        round(close_today, 2),
                        "pct_change_1d": round(pct_change, 2),
                        "above_sma10":  close_today > sma_10,
                    },
                )
                triggered_count += 1

            except Exception as e:
                log.debug(f"   VolumeScanner skip {ticker}: {e}")
                continue

        log.info(f"   📊 VolumeScanner: {triggered_count} signals found")
        return results
