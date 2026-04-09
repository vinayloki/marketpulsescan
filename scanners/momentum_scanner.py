"""
MarketPulse India — EMA + RSI Momentum Scanner

Signal: EMA(9) > EMA(21) > EMA(50)  [bullish EMA alignment]
        AND RSI(14) is between RSI_MOMENTUM_LOW and RSI_MOMENTUM_HIGH
        [momentum zone, not overbought]

Scoring (max 45 pts):
    - EMA alignment strength    : 0–20 pts
    - RSI position in zone      : 0–15 pts (sweet spot around 60)
    - 1-month return boost      : 0–10 pts (confirms underlying trend)
"""

import logging
import pandas as pd

from config.settings import (
    EMA_FAST, EMA_MID, EMA_SLOW,
    RSI_MOMENTUM_HIGH, RSI_MOMENTUM_LOW, RSI_PERIOD,
    TIMEFRAMES,
)
from engine.opportunity_model import ScanResult
from scanners.base_scanner import BaseScanner

log = logging.getLogger("marketpulse.momentum")


class MomentumScanner(BaseScanner):
    NAME = "EMA_MOMENTUM"
    MAX_SCORE = 45

    def scan(self, ohlcv: pd.DataFrame) -> dict[str, ScanResult]:
        """
        Scan for stocks in a confirmed bullish EMA trend with
        RSI in the healthy momentum zone (not overbought).

        EMA alignment condition: EMA9 > EMA21 > EMA50
        RSI condition: RSI_LOW <= RSI14 <= RSI_HIGH
        """
        results: dict[str, ScanResult] = {}

        if "Close" not in ohlcv.columns.get_level_values(0):
            log.warning("⚠️  MomentumScanner: No 'Close' column")
            return results

        close_df = ohlcv["Close"]
        triggered_count = 0
        one_month_days = TIMEFRAMES["1M"]  # 21

        for ticker in close_df.columns:
            try:
                close = close_df[ticker].dropna()

                # Need enough data for EMA(50) to be meaningful
                if len(close) < EMA_SLOW + 10:
                    continue

                # ── Compute indicators ────────────────────────────────
                ema9  = self._ema(close, EMA_FAST)
                ema21 = self._ema(close, EMA_MID)
                ema50 = self._ema(close, EMA_SLOW)
                rsi   = self._rsi(close, RSI_PERIOD)

                e9  = self._safe_last(ema9)
                e21 = self._safe_last(ema21)
                e50 = self._safe_last(ema50)
                rsi_val = self._safe_last(rsi)
                price = self._safe_last(close)

                if any(v is None for v in [e9, e21, e50, rsi_val, price]):
                    continue

                # ── Conditions ────────────────────────────────────────
                ema_aligned = e9 > e21 > e50
                rsi_in_zone = RSI_MOMENTUM_LOW <= rsi_val <= RSI_MOMENTUM_HIGH

                if not (ema_aligned and rsi_in_zone):
                    continue

                # ── Scoring ───────────────────────────────────────────

                # EMA alignment strength (0–20 pts)
                # Strength = how far apart the EMAs are relative to price
                ema9_21_gap  = (e9 - e21) / price * 100
                ema21_50_gap = (e21 - e50) / price * 100
                alignment_strength = (ema9_21_gap + ema21_50_gap) / 2
                ema_score = min(20, int(alignment_strength * 10))

                # RSI sweet spot scoring (0–15 pts)
                # Peak score at RSI=62, decays toward edges
                rsi_center = 62
                rsi_deviation = abs(rsi_val - rsi_center) / (rsi_center - RSI_MOMENTUM_LOW)
                rsi_score = max(0, int(15 * (1 - rsi_deviation)))

                # 1M return boost (0–10 pts)
                return_score = 0
                if len(close) >= one_month_days:
                    ret_1m = (price - float(close.iloc[-one_month_days])) / float(close.iloc[-one_month_days]) * 100
                    return_score = min(10, max(0, int(ret_1m / 2)))
                else:
                    ret_1m = None

                score = min(ema_score + rsi_score + return_score, self.MAX_SCORE)

                results[ticker] = ScanResult(
                    ticker=ticker,
                    scanner=self.NAME,
                    triggered=True,
                    score=score,
                    signals=["EMA_MOMENTUM"],
                    indicators={
                        "rsi_14":     round(rsi_val, 1),
                        "ema_9":      round(e9, 2),
                        "ema_21":     round(e21, 2),
                        "ema_50":     round(e50, 2),
                        "price":      round(price, 2),
                        "return_1m":  round(ret_1m, 2) if ret_1m else None,
                    },
                )
                triggered_count += 1

            except Exception as e:
                log.debug(f"   MomentumScanner skip {ticker}: {e}")
                continue

        log.info(f"   🚀 MomentumScanner: {triggered_count} signals found")
        return results
