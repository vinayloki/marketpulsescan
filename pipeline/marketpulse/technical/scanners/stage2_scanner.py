"""
MarketPulse — Stan Weinstein Stage 2 / Minervini Trend Template Scanner
"""

from __future__ import annotations

import logging

import pandas as pd

from marketpulse.sector import rs_rating
from marketpulse.technical.indicators import is_rising, sma
from marketpulse.technical.scanners.base_scanner import BaseScanner, ScanResult

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# MA periods for each timeframe.
# Daily  : Classic Minervini Trend Template (50 / 150 / 200 daily bars)
# Weekly : Stan Weinstein style    (10wk ≈ 50d  /  30wk ≈ 150d  /  40wk ≈ 200d)
# Monthly: Macro trend             (12mo / 24mo / 48mo)
# ─────────────────────────────────────────────────────────────────────────────
TIMEFRAME_PARAMS = {
    "daily": {"fast": 50, "mid": 150, "slow": 200, "min_bars": 210, "lookback_unit": 252},
    "weekly": {"fast": 10, "mid": 30, "slow": 40, "min_bars": 45, "lookback_unit": 52},
    "monthly": {"fast": 12, "mid": 24, "slow": 48, "min_bars": 50, "lookback_unit": 12},
}


class Stage2Scanner(BaseScanner):
    NAME = "STAGE_2"
    MAX_SCORE = 100

    def scan(  # type: ignore[override]
        self,
        ohlcv: pd.DataFrame,
        timeframe: str = "daily",
    ) -> dict[str, ScanResult]:
        """
        Scan for stocks meeting Stan Weinstein Stage 2 / Minervini Trend Template.
        """
        params = TIMEFRAME_PARAMS.get(timeframe, TIMEFRAME_PARAMS["daily"])
        fast = params["fast"]
        mid = params["mid"]
        slow = params["slow"]
        min_b = params["min_bars"]
        lu = params["lookback_unit"]  # bars in one "year" equivalent

        results: dict[str, ScanResult] = {}

        if "Close" not in ohlcv.columns.get_level_values(0):
            log.warning("Stage2Scanner: No 'Close' column (%s)", timeframe)
            return results

        close_df = ohlcv["Close"]
        high_df = ohlcv["High"] if "High" in ohlcv.columns.get_level_values(0) else close_df
        low_df = ohlcv["Low"] if "Low" in ohlcv.columns.get_level_values(0) else close_df

        rs_scores = rs_rating(ohlcv)

        tickers = close_df.columns.tolist()
        triggered_count = 0

        for ticker in tickers:
            try:
                close = close_df[ticker].dropna()
                if len(close) < min_b:
                    continue

                high = high_df[ticker].dropna()
                low = low_df[ticker].dropna()

                # ── Moving averages ──────────────────────────────────────────
                sma_fast = sma(close, fast)
                sma_mid = sma(close, mid)
                sma_slow = sma(close, slow)

                c_price = float(close.iloc[-1])
                c_sma_fast = float(sma_fast.iloc[-1])
                c_sma_mid = float(sma_mid.iloc[-1])
                c_sma_slow = float(sma_slow.iloc[-1])

                # ── 52-unit High / Low ───────────────────────────────────────
                high_52u = float(high.tail(lu).max())
                low_52u = float(low.tail(lu).min())

                # ── Slow MA trend ────────────────────────────────────────────
                slow_ma_rising = is_rising(sma_slow, min(20, len(sma_slow) - 1))

                # ── RS Rating ────────────────────────────────────────────────
                rs = float(rs_scores.get(ticker, 0)) if not rs_scores.empty else 0.0

                # ── 8-condition Trend Template ───────────────────────────────
                cond_1 = c_price > c_sma_mid and c_price > c_sma_slow
                cond_2 = c_sma_mid > c_sma_slow
                cond_3 = slow_ma_rising
                cond_4 = c_sma_fast > c_sma_mid and c_sma_fast > c_sma_slow
                cond_5 = c_price > c_sma_fast
                cond_6 = c_price >= (1.30 * low_52u)
                cond_7 = c_price >= (0.75 * high_52u)
                cond_8 = rs >= 70

                if all([cond_1, cond_2, cond_3, cond_4, cond_5, cond_6, cond_7, cond_8]):
                    pct_from_high = (high_52u - c_price) / high_52u * 100
                    score = min(100, int(rs * 0.7 + (25 - pct_from_high) * 1.2))

                    results[ticker] = ScanResult(
                        ticker=ticker,
                        scanner=self.NAME,
                        triggered=True,
                        score=score,
                        signals=["STAGE_2_UPTREND"],
                        indicators={
                            "price": round(c_price, 2),
                            "sma_50": round(c_sma_fast, 2),
                            "sma_150": round(c_sma_mid, 2),
                            "sma_200": round(c_sma_slow, 2),
                            "high_52w": round(high_52u, 2),
                            "low_52w": round(low_52u, 2),
                            "rs_rating": round(rs, 1),
                            "ema200_rising": slow_ma_rising,
                        },
                    )
                    triggered_count += 1

            except Exception as e:
                log.debug("Stage2Scanner skip %s (%s): %s", ticker, timeframe, e)

        log.info(
            "Stage2Scanner [%s]: %d/%d stocks meet Trend Template — MAs: %d/%d/%d",
            timeframe,
            triggered_count,
            len(tickers),
            fast,
            mid,
            slow,
        )
        return results
