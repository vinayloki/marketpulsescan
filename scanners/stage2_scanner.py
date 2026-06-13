import logging
import pandas as pd

from engine.indicators import calculate_sma, check_rising
from engine.relative_strength import calculate_rs_rating
from engine.opportunity_model import ScanResult

log = logging.getLogger("marketpulse.stage2")

# ─────────────────────────────────────────────────────────────────────────────
# MA periods for each timeframe.
# Daily  : Classic Minervini Trend Template (50 / 150 / 200 daily bars)
# Weekly : Stan Weinstein style    (10wk ≈ 50d  /  30wk ≈ 150d  /  40wk ≈ 200d)
# Monthly: Macro trend             (12mo / 24mo / 48mo)
# ─────────────────────────────────────────────────────────────────────────────
TIMEFRAME_PARAMS = {
    "daily":   {"fast": 50,  "mid": 150, "slow": 200, "min_bars": 210, "lookback_unit": 252},
    "weekly":  {"fast": 10,  "mid": 30,  "slow": 40,  "min_bars": 45,  "lookback_unit": 52},
    "monthly": {"fast": 12,  "mid": 24,  "slow": 48,  "min_bars": 50,  "lookback_unit": 12},
}


class Stage2Scanner:
    NAME = "STAGE_2"

    def scan(self, ohlcv: pd.DataFrame, timeframe: str = "daily") -> dict:
        """
        Scan for stocks meeting Stan Weinstein Stage 2 / Minervini Trend Template criteria.

        The exact MA periods depend on the timeframe:
        - daily  : 50 / 150 / 200 bars
        - weekly : 10 / 30  / 40  bars  (≈ Weinstein 10-week & 30-week)
        - monthly: 12 / 24  / 48  bars

        Rules (same logic, different periods):
        1. Price > fast MA and mid MA and slow MA
        2. mid MA > slow MA
        3. slow MA is trending up (higher than 20 bars ago)
        4. fast MA > mid MA and slow MA
        5. Price at least 30% above 52-unit low
        6. Price within 25% of 52-unit high
        7. RS Rating >= 70
        """
        params = TIMEFRAME_PARAMS.get(timeframe, TIMEFRAME_PARAMS["daily"])
        fast   = params["fast"]
        mid    = params["mid"]
        slow   = params["slow"]
        min_b  = params["min_bars"]
        lu     = params["lookback_unit"]   # bars in one "year" equivalent

        results = {}

        if "Close" not in ohlcv.columns.get_level_values(0):
            log.warning(f"No 'Close' column. Cannot run Stage 2 Scanner ({timeframe}).")
            return results

        close_df = ohlcv["Close"]
        high_df  = ohlcv["High"] if "High" in ohlcv.columns.get_level_values(0) else close_df
        low_df   = ohlcv["Low"]  if "Low"  in ohlcv.columns.get_level_values(0) else close_df

        rs_ratings = calculate_rs_rating(ohlcv)

        tickers = close_df.columns.tolist()
        triggered_count = 0

        for ticker in tickers:
            try:
                close = close_df[ticker].dropna()
                if len(close) < min_b:
                    continue  # not enough history for this timeframe

                high = high_df[ticker].dropna()
                low  = low_df[ticker].dropna()

                # ── Moving averages ────────────────────────────────────────
                sma_fast = calculate_sma(close, fast)
                sma_mid  = calculate_sma(close, mid)
                sma_slow = calculate_sma(close, slow)

                c_price    = close.iloc[-1]
                c_sma_fast = sma_fast.iloc[-1]
                c_sma_mid  = sma_mid.iloc[-1]
                c_sma_slow = sma_slow.iloc[-1]

                # ── 52-unit High / Low ─────────────────────────────────────
                high_52u = high.tail(lu).max()
                low_52u  = low.tail(lu).min()

                # ── Slow MA trend ──────────────────────────────────────────
                slow_ma_rising = check_rising(sma_slow, lookback=min(20, len(sma_slow) - 1))

                # ── RS Rating ─────────────────────────────────────────────
                rs = rs_ratings.get(ticker, 0)

                # ── 8-condition Trend Template ─────────────────────────────
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
                            "price":       round(c_price, 2),
                            "sma_50":      round(c_sma_fast, 2),   # stored generically as sma_50 key
                            "sma_150":     round(c_sma_mid, 2),
                            "sma_200":     round(c_sma_slow, 2),
                            "high_52w":    round(high_52u, 2),
                            "low_52w":     round(low_52u, 2),
                            "rs_rating":   round(rs, 1),
                            "ema200_rising": slow_ma_rising,
                        },
                    )
                    triggered_count += 1

            except Exception as e:
                log.debug(f"Stage2Scanner skip {ticker} ({timeframe}): {e}")

        log.info(
            f"📈 Stage2Scanner [{timeframe}]: {triggered_count}/{len(tickers)} "
            f"stocks meet Trend Template — MAs: {fast}/{mid}/{slow}"
        )
        return results
