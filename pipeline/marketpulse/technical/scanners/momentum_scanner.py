"""
MarketPulse — EMA + RSI Momentum Scanner
"""

from __future__ import annotations

import logging

import pandas as pd

from marketpulse.config.settings import (
    EMA_FAST,
    EMA_MID,
    EMA_SLOW,
    RSI_MOMENTUM_HIGH,
    RSI_MOMENTUM_LOW,
    RSI_PERIOD,
)
from marketpulse.technical.scanners.base_scanner import BaseScanner, ScanResult

log = logging.getLogger(__name__)


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
            log.warning("MomentumScanner: No 'Close' column")
            return results

        close_df = ohlcv["Close"]
        triggered_count = 0
        one_month_days = 21  # 21 trading days in a month

        for ticker in close_df.columns:
            try:
                close = close_df[ticker].dropna()

                # Need enough data for EMA(slow) to be meaningful
                if len(close) < EMA_SLOW + 10:
                    continue

                # ── Compute indicators ────────────────────────────────
                ema9 = self._ema(close, EMA_FAST)
                ema21 = self._ema(close, EMA_MID)
                ema50 = self._ema(close, EMA_SLOW)
                rsi = self._rsi(close, RSI_PERIOD)

                e9 = self._safe_last(ema9)
                e21 = self._safe_last(ema21)
                e50 = self._safe_last(ema50)
                rsi_val = self._safe_last(rsi)
                price = self._safe_last(close)

                if any(v is None for v in [e9, e21, e50, rsi_val, price]):
                    continue

                assert e9 is not None and e21 is not None and e50 is not None
                assert rsi_val is not None and price is not None

                # ── Conditions ────────────────────────────────────────
                ema_aligned = e9 > e21 > e50
                rsi_in_zone = RSI_MOMENTUM_LOW <= rsi_val <= RSI_MOMENTUM_HIGH

                if not (ema_aligned and rsi_in_zone):
                    continue

                # ── Scoring ───────────────────────────────────────────

                # EMA alignment strength (0-20 pts)
                ema9_21_gap = (e9 - e21) / price * 100
                ema21_50_gap = (e21 - e50) / price * 100
                alignment_strength = (ema9_21_gap + ema21_50_gap) / 2
                ema_score = min(20, int(alignment_strength * 10))

                # RSI sweet spot scoring (0-15 pts)
                # Peak score at RSI=62, decays toward edges
                rsi_center = 62
                rsi_deviation = abs(rsi_val - rsi_center) / (rsi_center - RSI_MOMENTUM_LOW)
                rsi_score = max(0, int(15 * (1 - rsi_deviation)))

                # 1M return boost (0-10 pts)
                ret_1m: float | None = None
                return_score = 0
                if len(close) >= one_month_days:
                    ret_1m = (
                        (price - float(close.iloc[-one_month_days]))
                        / float(close.iloc[-one_month_days])
                        * 100
                    )
                    return_score = min(10, max(0, int(ret_1m / 2)))

                score = min(ema_score + rsi_score + return_score, self.MAX_SCORE)

                results[ticker] = ScanResult(
                    ticker=ticker,
                    scanner=self.NAME,
                    triggered=True,
                    score=score,
                    signals=["EMA_MOMENTUM"],
                    indicators={
                        "rsi_14": round(rsi_val, 1),
                        "ema_9": round(e9, 2),
                        "ema_21": round(e21, 2),
                        "ema_50": round(e50, 2),
                        "price": round(price, 2),
                        "return_1m": round(ret_1m, 2) if ret_1m is not None else None,
                    },
                )
                triggered_count += 1

            except Exception as e:
                log.debug("MomentumScanner skip %s: %s", ticker, e)
                continue

        log.info("MomentumScanner: %d signals found", triggered_count)
        return results
