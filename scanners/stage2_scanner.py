import logging
import pandas as pd

from engine.indicators import calculate_sma, calculate_ema, check_rising
from engine.relative_strength import calculate_rs_rating
from engine.opportunity_model import ScanResult

log = logging.getLogger("marketpulse.stage2")

class Stage2Scanner:
    NAME = "STAGE_2"
    
    def scan(self, ohlcv: pd.DataFrame) -> dict:
        """
        Scan for stocks meeting Mark Minervini's Trend Template / Stan Weinstein's Stage 2 criteria.
        
        Rules:
        1. Current price is > 150-day (30-week) and 200-day SMA.
        2. 150-day SMA > 200-day SMA.
        3. 200-day SMA is trending up (higher than 20 days ago).
        4. 50-day SMA > 150-day and 200-day SMA.
        5. Current price > 50-day SMA.
        6. Current price is at least 30% above 52-week low.
        7. Current price is within 25% of 52-week high.
        8. RS Rating is >= 70.
        """
        results = {}
        
        if "Close" not in ohlcv.columns.get_level_values(0):
            log.warning("No 'Close' column. Cannot run Stage 2 Scanner.")
            return results

        close_df = ohlcv["Close"]
        high_df = ohlcv["High"] if "High" in ohlcv.columns.get_level_values(0) else close_df
        low_df = ohlcv["Low"] if "Low" in ohlcv.columns.get_level_values(0) else close_df
        
        # Calculate RS Ratings
        rs_ratings = calculate_rs_rating(ohlcv)

        tickers = close_df.columns.tolist()
        triggered_count = 0

        for ticker in tickers:
            try:
                close = close_df[ticker].dropna()
                if len(close) < 252:
                    continue # Need at least 252 days for 200 SMA and 52-week high/low
                
                high = high_df[ticker].dropna()
                low = low_df[ticker].dropna()
                
                # Moving Averages
                sma_50 = calculate_sma(close, 50)
                sma_150 = calculate_sma(close, 150)
                sma_200 = calculate_sma(close, 200)
                
                c_price = close.iloc[-1]
                c_sma_50 = sma_50.iloc[-1]
                c_sma_150 = sma_150.iloc[-1]
                c_sma_200 = sma_200.iloc[-1]
                
                # 52-week High/Low
                high_52w = high.tail(252).max()
                low_52w = low.tail(252).min()
                
                # Trend of 200-day SMA
                sma_200_rising = check_rising(sma_200, lookback=20)
                
                # RS Rating
                rs = rs_ratings.get(ticker, 0)
                
                # Condition Checks
                cond_1 = c_price > c_sma_150 and c_price > c_sma_200
                cond_2 = c_sma_150 > c_sma_200
                cond_3 = sma_200_rising
                cond_4 = c_sma_50 > c_sma_150 and c_sma_50 > c_sma_200
                cond_5 = c_price > c_sma_50
                cond_6 = c_price >= (1.30 * low_52w)
                cond_7 = c_price >= (0.75 * high_52w)
                cond_8 = rs >= 70
                
                stage_2_criteria_met = all([cond_1, cond_2, cond_3, cond_4, cond_5, cond_6, cond_7, cond_8])
                
                if stage_2_criteria_met:
                    # Score can be derived from RS rating and proximity to 52w high
                    pct_from_high = (high_52w - c_price) / high_52w * 100
                    score = min(100, int(rs * 0.7 + (25 - pct_from_high) * 1.2))
                    
                    results[ticker] = ScanResult(
                        ticker=ticker,
                        scanner=self.NAME,
                        triggered=True,
                        score=score,
                        signals=["STAGE_2_UPTREND"],
                        indicators={
                            "price": round(c_price, 2),
                            "sma_50": round(c_sma_50, 2),
                            "sma_150": round(c_sma_150, 2),
                            "sma_200": round(c_sma_200, 2),
                            "high_52w": round(high_52w, 2),
                            "low_52w": round(low_52w, 2),
                            "rs_rating": round(rs, 1)
                        }
                    )
                    triggered_count += 1
            except Exception as e:
                log.debug(f"Stage2Scanner skip {ticker}: {e}")
                
        log.info(f"📈 Stage2Scanner: {triggered_count} stocks meet Trend Template criteria.")
        return results
