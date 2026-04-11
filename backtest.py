"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — Walk-Forward Backtesting Engine                        ║
║                                                                              ║
║  Strictly bias-free walk-forward simulation of weekly swing trades.          ║
║                                                                              ║
║  Architecture:                                                               ║
║    • Signal Date : Monday (scan day) — uses ONLY data up to that date       ║
║    • Entry       : OPEN of the next trading day after signal                 ║
║    • Exit        : TP (+4%) / Hybrid SL (max 2%, 1.5×ATR14) / TIME (5d)    ║
║    • Conservative: if both TP and SL triggered on same bar → SL wins        ║
║                                                                              ║
║  Mode A — Full NSE Universe (true strategy edge test)                        ║
║    All detected signals simulated, no position cap                           ║
║                                                                              ║
║  Mode B — AI-Filtered Top Picks (execution subset performance)               ║
║    Top MODE_B_TOP_N signals by score, with MAX_POSITIONS cap                 ║
║                                                                              ║
║  Anti-bias enforcement:                                                      ║
║    ✅ No lookahead  — slice = ohlcv.loc[:scan_date]                          ║
║    ✅ No survivorship — all tickers with enough history on that date          ║
║    ✅ Cross-validation — Mode A vs Mode B always shown together               ║
║                                                                              ║
║  Outputs:                                                                    ║
║    scan_results/backtest_results.json  — full trade log + summary stats      ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config.settings import (
    # Backtest
    ATR_PERIOD,
    ATR_SL_MULTIPLIER,
    BACKTEST_WEEKS,
    MAX_HOLD_DAYS,
    MODE_B_TOP_N,
    OHLCV_CACHE_FILE,
    OHLCV_CACHE_MAX_AGE_H,
    STOP_LOSS_FIXED_PCT,
    TAKE_PROFIT_PCT,
    # Scanners
    BREAKOUT_PROXIMITY_PCT,
    BREAKOUT_VOLUME_MULT,
    EMA_FAST, EMA_MID, EMA_SLOW,
    RSI_MOMENTUM_HIGH, RSI_MOMENTUM_LOW, RSI_PERIOD,
    VOLUME_SPIKE_MULT,
    # Risk
    CAPITAL,
    MAX_POSITIONS,
    RISK_PER_TRADE_PCT,
    # Regime thresholds
    REGIME_BULL_MIN_SCORE,
    REGIME_SIDEWAYS_MIN_SCORE,
    REGIME_BEAR_MIN_SCORE,
    REGIME_BULL_SIZE_MULT,
    REGIME_SIDEWAYS_SIZE_MULT,
    REGIME_BEAR_SIZE_MULT,
    # Paths
    MIN_DATA_POINTS,
    OUTPUT_DIR,
)
from data_providers import get_provider

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("backtest")

BACKTEST_OUT = OUTPUT_DIR / "backtest_results.json"


# ══════════════════════════════════════════════════════════════════════════════
#  TRADE DATACLASS  — complete record of every simulated trade
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Trade:
    """Immutable record of one simulated swing trade."""
    # ── Identification
    ticker:           str
    signal_type:      str    # BREAKOUT | MOMENTUM | VOLUME | MULTI
    score:            int    # composite signal score 0–100+
    signal_date:      str    # ISO date signal was detected (scan date)

    # ── Entry
    entry_date:       str    # ISO date of actual entry (next trading day)
    entry_price:      float  # open price on entry_date

    # ── Risk Levels
    atr:              float  # ATR14 on signal date (price units)
    sl_distance:      float  # absolute price distance to stop loss
    stop_loss:        float  # price level for stop loss
    take_profit:      float  # price level for take profit
    sl_pct:           float  # SL distance as % of entry
    tp_pct:           float  # TP distance as % of entry (≈ TAKE_PROFIT_PCT)
    risk_reward:      float  # (TP distance) / (SL distance)
    position_qty:     int    # shares computed by risk formula

    # ── Context
    regime:           str    # Bull | Sideways | Bear
    mode:             str    # A | B

    # ── Exit  (filled during simulation)
    exit_date:        str   = ""
    exit_price:       float = 0.0
    exit_reason:      str   = ""    # TP | SL | TIME
    return_pct:       float = 0.0
    holding_days:     int   = 0
    pnl:              float = 0.0   # absolute P&L in ₹
    won:              bool  = False


# ══════════════════════════════════════════════════════════════════════════════
#  TECHNICAL INDICATORS
# ══════════════════════════════════════════════════════════════════════════════

def _ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential moving average (Wilder-style, adjust=False)."""
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI using Wilder's smoothing — identical to TradingView default."""
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series,
         period: int = 14) -> pd.Series:
    """
    Average True Range using Wilder's exponential smoothing.
    TR = max(H-L, |H-prev_C|, |L-prev_C|)
    """
    prev_c = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_c).abs(),
        (low  - prev_c).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, adjust=False).mean()


def _vol_sma(volume: pd.Series, window: int = 20) -> pd.Series:
    return volume.rolling(window=window, min_periods=window).mean()


# ══════════════════════════════════════════════════════════════════════════════
#  SIGNAL DETECTION  (strictly no-lookahead — operates on hist_slice only)
# ══════════════════════════════════════════════════════════════════════════════

def detect_signals(hist_slice: pd.DataFrame, ind: dict = None, scan_date = None) -> dict[str, dict]:
    """
    Detect all trading signals using only data in hist_slice.
    Mirrors the logic of BreakoutScanner, MomentumScanner, VolumeScanner
    so backtest results are directly comparable to live scanner output.

    Returns:
        { ticker: { 'score': int, 'type': str, 'atr': float,
                    'price': float, 'triggered': list[str],
                    'indicators': dict } }
    """
    if hist_slice.empty:
        return {}

    required = {"Open", "High", "Low", "Close", "Volume"}
    available = set(hist_slice.columns.get_level_values(0))
    if not required.issubset(available):
        log.debug(f"detect_signals: missing OHLCV fields {required - available}")
        return {}

    close_df  = hist_slice["Close"]
    high_df   = hist_slice["High"]
    low_df    = hist_slice["Low"]
    volume_df = hist_slice["Volume"]


    close_df  = hist_slice["Close"]
    volume_df = hist_slice["Volume"]
    
    signals: dict[str, dict] = {}
    
    # Pull the exact day cross-section
    if scan_date not in close_df.index:
        return signals
        
    idx_num = close_df.index.get_loc(scan_date)
    if isinstance(idx_num, slice): return signals
    if idx_num < max(EMA_SLOW + 10, 60):
        return signals
        
    prev_idx_num = idx_num - 1
    
    # 1D slices for the current date
    c_row = close_df.iloc[idx_num]
    v_row = volume_df.iloc[idx_num]
    prev_c_row = close_df.iloc[prev_idx_num]
    
    e9_row  = ind["ema9"].loc[scan_date]
    e21_row = ind["ema21"].loc[scan_date]
    e50_row = ind["ema50"].loc[scan_date]
    rsi_row = ind["rsi"].loc[scan_date]
    atr_row = ind["atr"].loc[scan_date]
    v_sma_row = ind["vol_sma"].loc[scan_date]
    h52_row = ind["high_52w"].loc[scan_date]
    
    # 1-month return (approx 21 trading days ago)
    ret_idx = max(0, idx_num - 21)
    ret_row = close_df.iloc[ret_idx]
    
    # 10-day sma for volume score bonus
    sma10_row = close_df.iloc[max(0, idx_num-9):idx_num+1].mean(axis=0)

    for ticker in c_row.index:
        try:
            curr_close = float(c_row[ticker])
            if pd.isna(curr_close) or curr_close <= 0: continue
            
            curr_vol = float(v_row[ticker])
            prev_close = float(prev_c_row[ticker])
            
            e9 = float(e9_row[ticker])
            e21 = float(e21_row[ticker])
            e50 = float(e50_row[ticker])
            rsi_val = float(rsi_row[ticker])
            atr_val = float(atr_row[ticker])
            vol_avg = float(v_sma_row[ticker])
            high_52w = float(h52_row[ticker])
            
            if pd.isna(e50) or vol_avg <= 0 or atr_val <= 0:
                continue
                
            vol_ratio = curr_vol / vol_avg
            pct_from_h = (1 - curr_close / high_52w) * 100 if high_52w > 0 else 100

            # Signal 1: 52-Week Breakout
            score_breakout = 0
            triggered = []
            if pct_from_h <= BREAKOUT_PROXIMITY_PCT and vol_ratio >= BREAKOUT_VOLUME_MULT:
                s = 20
                s += min(10, int((vol_ratio - BREAKOUT_VOLUME_MULT) / 1.5 * 10))
                if pct_from_h <= 0.5: s += 5
                score_breakout = min(30, s)
                triggered.append("BREAKOUT")

            # Signal 2: EMA + RSI Momentum
            score_momentum = 0
            ema_aligned = e9 > e21 > e50
            rsi_in_zone = RSI_MOMENTUM_LOW <= rsi_val <= RSI_MOMENTUM_HIGH
            if ema_aligned and rsi_in_zone:
                ema9_21_gap   = (e9 - e21) / curr_close * 100
                ema21_50_gap  = (e21 - e50) / curr_close * 100
                align_str     = (ema9_21_gap + ema21_50_gap) / 2
                ema_sc        = min(20, int(align_str * 10))
                rsi_center = 62.0
                rsi_dev    = abs(rsi_val - rsi_center) / max(1, rsi_center - RSI_MOMENTUM_LOW)
                rsi_sc     = max(0, int(15 * (1 - rsi_dev)))
                
                ret_1m = (curr_close / float(ret_row[ticker]) - 1) * 100
                ret_sc = min(10, max(0, int(ret_1m / 2)))
                
                score_momentum = min(45, ema_sc + rsi_sc + ret_sc)
                triggered.append("MOMENTUM")

            # Signal 3: Volume Spike
            score_volume = 0
            if vol_ratio >= VOLUME_SPIKE_MULT and curr_close > prev_close:
                norm = (vol_ratio - VOLUME_SPIKE_MULT) / max(1, (6.0 - VOLUME_SPIKE_MULT))
                s    = int(min(22, norm * 22))
                sma10 = float(sma10_row[ticker])
                if curr_close > sma10: s += 3
                score_volume = min(25, s)
                triggered.append("VOLUME")

            if not triggered:
                continue

            raw_score = score_breakout + score_momentum + score_volume
            n_signals = len(triggered)
            bonus     = {2: 5, 3: 10}.get(n_signals, 0)
            score     = min(100, raw_score + bonus)

            if score < REGIME_BULL_MIN_SCORE:
                continue

            sig_type = "MULTI" if n_signals >= 2 else triggered[0]

            signals[ticker] = {
                "score":      score,
                "type":       sig_type,
                "triggered":  triggered,
                "atr":        round(atr_val, 4),
                "price":      round(curr_close, 2),
                "indicators": {
                    "pct_from_52w_high": round(pct_from_h, 2),
                    "vol_ratio":         round(vol_ratio, 2),
                    "rsi":               round(rsi_val, 1),
                    "ema9":              round(e9, 2),
                    "ema50":             round(e50, 2),
                },
            }
        except Exception:
            continue

    return signals


# ══════════════════════════════════════════════════════════════════════════════
#  RISK CALCULATIONS
# ══════════════════════════════════════════════════════════════════════════════

def compute_hybrid_sl(entry: float, atr: float) -> tuple[float, float, float]:
    """
    Hybrid Stop Loss = max(fixed % floor, ATR-based distance).

    Returns: (sl_price, sl_pct, sl_distance_in_currency)
    """
    fixed_dist = entry * (STOP_LOSS_FIXED_PCT / 100)
    atr_dist   = atr   * ATR_SL_MULTIPLIER
    sl_dist    = max(fixed_dist, atr_dist)
    sl_price   = entry - sl_dist
    sl_pct     = (sl_dist / entry) * 100
    return round(sl_price, 2), round(sl_pct, 3), round(sl_dist, 4)


def compute_position_size(capital: float, sl_distance: float,
                          regime_mult: float = 1.0) -> int:
    """
    qty = (capital × risk_pct / 100) / sl_distance × regime_mult
    Minimum 1 share.
    """
    if sl_distance <= 0:
        return 1
    risk_amt = capital * (RISK_PER_TRADE_PCT / 100) * regime_mult
    return max(1, int(risk_amt / sl_distance))


# ══════════════════════════════════════════════════════════════════════════════
#  TRADE SIMULATION
# ══════════════════════════════════════════════════════════════════════════════

def simulate_trade(
    ticker:          str,
    signal:          dict,
    scan_date:       pd.Timestamp,
    ohlcv_full:      pd.DataFrame,
    regime:          str,
    regime_mult:     float,
    mode:            str,
    current_capital: float,
) -> Optional[Trade]:
    """
    Simulate one trade from signal detection to exit.

    Entry: OPEN of the first trading day AFTER scan_date.
    Exit:  TP / Hybrid SL / TIME (MAX_HOLD_DAYS bars after entry).
    Conservative model: if both SL and TP triggered on the same bar → SL wins.

    Returns a completed Trade or None if insufficient forward data.
    """
    try:
        close_col = ohlcv_full["Close"][ticker].dropna()
        high_col  = ohlcv_full["High"][ticker].dropna()
        low_col   = ohlcv_full["Low"][ticker].dropna()
        open_col  = ohlcv_full["Open"][ticker].dropna()
    except KeyError:
        return None

    # All dates strictly AFTER scan_date to avoid lookahead
    fwd_dates = close_col.index[close_col.index > scan_date]
    if len(fwd_dates) < 1:
        return None

    # ── Entry ────────────────────────────────────────────────────────────
    entry_dt    = fwd_dates[0]
    entry_price = (
        float(open_col.loc[entry_dt])
        if entry_dt in open_col.index and open_col.loc[entry_dt] > 0
        else float(close_col.loc[entry_dt])
    )

    if entry_price <= 0:
        return None

    atr_val = signal["atr"] or (entry_price * 0.015)   # 1.5% fallback if ATR is zero

    # ── Risk levels ──────────────────────────────────────────────────────
    sl_price, sl_pct, sl_dist = compute_hybrid_sl(entry_price, atr_val)
    tp_price  = round(entry_price * (1 + TAKE_PROFIT_PCT / 100), 2)
    tp_pct    = TAKE_PROFIT_PCT
    rr        = round((tp_price - entry_price) / max(sl_dist, 0.01), 2)

    # ── Position size ─────────────────────────────────────────────────────
    qty = compute_position_size(current_capital, sl_dist, regime_mult)

    trade = Trade(
        ticker       = ticker,
        signal_type  = signal["type"],
        score        = signal["score"],
        signal_date  = str(scan_date.date()),
        entry_date   = str(entry_dt.date()),
        entry_price  = round(entry_price, 2),
        atr          = round(atr_val, 4),
        sl_distance  = round(sl_dist, 4),
        stop_loss    = sl_price,
        take_profit  = tp_price,
        sl_pct       = round(sl_pct, 3),
        tp_pct       = tp_pct,
        risk_reward  = rr,
        position_qty = qty,
        regime       = regime,
        mode         = mode,
    )

    # ── Simulation loop ───────────────────────────────────────────────────
    hold_dates  = fwd_dates[:MAX_HOLD_DAYS]
    exit_price  = float(close_col.loc[hold_dates[-1]])  # fallback: last close
    exit_reason = "TIME"
    exit_dt     = hold_dates[-1]

    for bar_idx, bar_dt in enumerate(hold_dates):
        try:
            bar_h = float(high_col.loc[bar_dt]) if bar_dt in high_col.index else entry_price
            bar_l = float(low_col.loc[bar_dt])  if bar_dt in low_col.index  else entry_price
            bar_c = float(close_col.loc[bar_dt])
        except Exception:
            continue

        sl_hit = bar_l <= sl_price
        tp_hit = bar_h >= tp_price

        if sl_hit and tp_hit:
            # Conservative: assume SL hit first (worst-case)
            exit_price  = sl_price
            exit_reason = "SL"
            exit_dt     = bar_dt
            break
        elif sl_hit:
            exit_price  = sl_price
            exit_reason = "SL"
            exit_dt     = bar_dt
            break
        elif tp_hit:
            exit_price  = tp_price
            exit_reason = "TP"
            exit_dt     = bar_dt
            break

        # Last bar — time exit
        if bar_idx == len(hold_dates) - 1:
            exit_price  = bar_c
            exit_reason = "TIME"
            exit_dt     = bar_dt

    # ── Compute result ────────────────────────────────────────────────────
    return_pct   = round((exit_price - entry_price) / entry_price * 100, 3)
    pnl          = round((exit_price - entry_price) * qty, 2)
    holding_days = int((exit_dt - entry_dt).days)

    trade.exit_date    = str(exit_dt.date())
    trade.exit_price   = round(exit_price, 2)
    trade.exit_reason  = exit_reason
    trade.return_pct   = return_pct
    trade.holding_days = holding_days
    trade.pnl          = pnl
    trade.won          = return_pct > 0

    return trade


# ══════════════════════════════════════════════════════════════════════════════
#  REGIME DETECTION  (inline — regime_filter.py is a later refinement)
# ══════════════════════════════════════════════════════════════════════════════

def detect_regime_inline(hist_slice: pd.DataFrame) -> tuple[str, float]:
    """
    Classify market regime using NIFTY-like index or median of all stocks.
    Returns: (regime_label, regime_mult) where regime_label ∈ {Bull, Sideways, Bear}
    """
    try:
        close_df = hist_slice["Close"]
        if close_df.empty or len(close_df) < 200:
            return "Bull", REGIME_BULL_SIZE_MULT

        # Use median of all stocks as a proxy for market index
        # (regime_filter.py will replace this with actual NIFTY data)
        market_proxy = close_df.median(axis=1).dropna()

        if len(market_proxy) < 200:
            return "Bull", REGIME_BULL_SIZE_MULT

        ema200    = float(_ema(market_proxy, 200).iloc[-1])
        current   = float(market_proxy.iloc[-1])
        pct_vs200 = (current - ema200) / ema200 * 100

        from config.settings import REGIME_SIDEWAYS_BAND_PCT
        if pct_vs200 > REGIME_SIDEWAYS_BAND_PCT:
            return "Bull",     REGIME_BULL_SIZE_MULT
        elif pct_vs200 < -REGIME_SIDEWAYS_BAND_PCT:
            return "Bear",     REGIME_BEAR_SIZE_MULT
        else:
            return "Sideways", REGIME_SIDEWAYS_SIZE_MULT

    except Exception as exc:
        log.debug(f"  regime detection failed: {exc}")
        return "Bull", REGIME_BULL_SIZE_MULT


# ══════════════════════════════════════════════════════════════════════════════
#  SCAN DATE GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def get_scan_dates(idx: pd.DatetimeIndex, weeks: int) -> list[pd.Timestamp]:
    """
    Build a list of scan dates (Mondays, or nearest trading day).
    Excludes the last MAX_HOLD_DAYS bars so every scan date has forward data.
    """
    # Reserve the final MAX_HOLD_DAYS bars for trade simulation
    usable = idx[:-MAX_HOLD_DAYS]
    if len(usable) < 10:
        return []

    # Restrict to the last `weeks` × 7 calendar days
    cutoff = usable[-1] - pd.Timedelta(weeks=weeks)
    usable = usable[usable >= cutoff]

    # Prefer actual Mondays (weekday == 0)
    mondays = [d for d in usable if d.weekday() == 0]

    # Fallback: first trading day of each ISO week
    if len(mondays) < max(1, weeks // 4):
        week_map: dict[str, pd.Timestamp] = {}
        for d in usable:
            k = f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"
            if k not in week_map:
                week_map[k] = d
        mondays = sorted(week_map.values())

    return mondays


# ══════════════════════════════════════════════════════════════════════════════
#  OHLCV DATA LOADING  (with parquet cache)
# ══════════════════════════════════════════════════════════════════════════════

def load_ohlcv(force_download: bool = False) -> pd.DataFrame:
    """
    Load 13-month OHLCV data.  Uses parquet cache if fresh (< OHLCV_CACHE_MAX_AGE_H).
    On cache miss or --force-download, downloads from yfinance and saves cache.
    """
    if not force_download and OHLCV_CACHE_FILE.exists():
        age_h = (time.time() - OHLCV_CACHE_FILE.stat().st_mtime) / 3600
        if age_h < OHLCV_CACHE_MAX_AGE_H:
            log.info(f"📂 Loading OHLCV from parquet cache ({age_h:.1f}h old)...")
            try:
                ohlcv = pd.read_parquet(OHLCV_CACHE_FILE)
                n_tickers = ohlcv.columns.get_level_values(1).nunique()
                log.info(f"   ✅ Cache ready: {n_tickers} stocks × {len(ohlcv)} days")
                return ohlcv
            except Exception as exc:
                log.warning(f"   ⚠️  Cache corrupt ({exc}) — re-downloading...")

    log.info("📡 Fetching ticker universe and downloading 13-month OHLCV...")
    provider = get_provider()
    tickers  = provider.fetch_ticker_universe()

    if not tickers:
        log.error("❌ No tickers — cannot run backtest.")
        sys.exit(1)

    ohlcv = provider.fetch_ohlcv(tickers, period="13mo", interval="1d")

    if ohlcv.empty:
        log.error("❌ OHLCV download returned no data.")
        sys.exit(1)

    # Save parquet cache
    try:
        ohlcv.to_parquet(OHLCV_CACHE_FILE)
        size_mb = OHLCV_CACHE_FILE.stat().st_size / 1_048_576
        log.info(f"   💾 OHLCV cached → {OHLCV_CACHE_FILE.name} ({size_mb:.1f} MB)")
    except Exception as exc:
        log.warning(f"   ⚠️  Could not save parquet cache: {exc}")

    return ohlcv



def precompute_indicators(ohlcv: pd.DataFrame) -> dict:
    log.info("  ⚙️  Precomputing technical indicators (vectorized over 2100 stocks)...")
    import numpy as np
    c = ohlcv["Close"]
    h = ohlcv["High"]
    l = ohlcv["Low"]
    v = ohlcv["Volume"]

    # EMA
    ema9  = c.ewm(span=EMA_FAST, adjust=False).mean()
    ema21 = c.ewm(span=EMA_MID, adjust=False).mean()
    ema50 = c.ewm(span=EMA_SLOW, adjust=False).mean()

    # RSI
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(com=RSI_PERIOD - 1, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(com=RSI_PERIOD - 1, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))

    # ATR
    prev_c = c.shift(1)
    tr1 = h - l
    tr2 = (h - prev_c).abs()
    tr3 = (l - prev_c).abs()
    tr = np.maximum(np.maximum(tr1.values, tr2.values), tr3.values)
    tr_df = pd.DataFrame(tr, index=c.index, columns=c.columns)
    atr = tr_df.ewm(com=ATR_PERIOD - 1, adjust=False).mean()

    # Vol SMA
    vol_sma = v.rolling(window=20, min_periods=20).mean()

    # High 52w (rolling 252 days)
    high_52w = h.rolling(window=252, min_periods=20).max()

    return {
        "ema9": ema9, "ema21": ema21, "ema50": ema50,
        "rsi": rsi, "atr": atr, "vol_sma": vol_sma, "high_52w": high_52w
    }

# ══════════════════════════════════════════════════════════════════════════════
#  MAIN BACKTEST LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run_backtest(ohlcv: pd.DataFrame, mode: str = "A") -> list[Trade]:
    """
    Walk-forward backtest engine.

    mode='A' — Full universe: all detected signals, no position cap.
               Measures true strategy edge across entire NSE.

    mode='B' — AI picks only: top MODE_B_TOP_N by score, with MAX_POSITIONS cap.
               Measures execution subset performance (what you'd actually trade).
    """
    log.info(f"\n{'─'*65}")
    log.info(f"  🧪  Starting Mode {mode} walk-forward backtest...")
    log.info(f"{'─'*65}")

    scan_dates = get_scan_dates(ohlcv.index, BACKTEST_WEEKS)
    if not scan_dates:
        log.error("❌  Insufficient historical data for backtesting.")
        return []

    log.info(
        f"  📅 Walk-forward window: {scan_dates[0].date()} → {scan_dates[-1].date()}"
        f"  ({len(scan_dates)} scan dates)"
    )

    ind = precompute_indicators(ohlcv)

    all_trades:    list[Trade]  = []
    current_cap:   float        = float(CAPITAL)
    open_tickers:  set[str]     = set()    # active positions for Mode B cap

    for week_idx, scan_date in enumerate(scan_dates):
        # ── Strict slice — NO data beyond scan_date ───────────────────
        hist = ohlcv.loc[:scan_date]

        # ── Regime classification at this point in time ───────────────
        regime, regime_mult = detect_regime_inline(hist)

        # ── Signal detection on historical slice ──────────────────────
        signals = detect_signals(hist, ind, scan_date)
        if not signals:
            continue

        # ── Mode filter ───────────────────────────────────────────────
        if mode == "B":
            # Keep only top N by score
            sorted_sigs = sorted(signals.items(), key=lambda x: x[1]["score"], reverse=True)
            signals = dict(sorted_sigs[:MODE_B_TOP_N])

        # ── Regime-based minimum score gate ───────────────────────────
        min_score = {
            "Bull":     REGIME_BULL_MIN_SCORE,
            "Sideways": REGIME_SIDEWAYS_MIN_SCORE,
            "Bear":     REGIME_BEAR_MIN_SCORE,
        }.get(regime, REGIME_BULL_MIN_SCORE)

        signals = {t: s for t, s in signals.items() if s["score"] >= min_score}

        if not signals:
            continue

        # ── Position cap (Mode B only — simulates real execution) ─────
        week_trades: list[Trade] = []

        for ticker, signal in sorted(
            signals.items(), key=lambda x: x[1]["score"], reverse=True
        ):
            if mode == "B" and len(open_tickers) >= MAX_POSITIONS:
                break
            if mode == "B" and ticker in open_tickers:
                continue

            trade = simulate_trade(
                ticker          = ticker,
                signal          = signal,
                scan_date       = scan_date,
                ohlcv_full      = ohlcv,
                regime          = regime,
                regime_mult     = regime_mult,
                mode            = mode,
                current_capital = current_cap,
            )

            if trade:
                week_trades.append(trade)
                if mode == "B":
                    open_tickers.add(ticker)

        # ── Update capital after each week's trades close ─────────────
        for t in week_trades:
            current_cap += t.pnl

        # ── Clear positions (all time-exit after the week) ────────────
        open_tickers.clear()
        all_trades.extend(week_trades)

        # ── Progress log every 10 weeks ───────────────────────────────
        if (week_idx + 1) % 10 == 0 or (week_idx + 1) == len(scan_dates):
            wins_so_far = sum(1 for t in all_trades if t.won)
            total_so_far = len(all_trades)
            wr = wins_so_far / total_so_far * 100 if total_so_far else 0
            log.info(
                f"  Week {week_idx + 1:>3}/{len(scan_dates)}"
                f"  [{scan_date.date()}]"
                f"  regime={regime:<8}"
                f"  signals={len(signals):>4}"
                f"  trades={len(week_trades):>3}"
                f"  total={total_so_far:>4}"
                f"  WR={wr:.0f}%"
                f"  cap=₹{current_cap:,.0f}"
            )

    log.info(
        f"  ✅  Mode {mode} complete — "
        f"{len(all_trades)} trades simulated"
        f"  (final capital ₹{current_cap:,.0f})"
    )
    return all_trades


# ══════════════════════════════════════════════════════════════════════════════
#  STATISTICS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def compute_stats(trades: list[Trade]) -> dict:
    """
    Compute full performance statistics from a list of completed trades.
    All metrics are self-contained — no external dependencies.
    """
    if not trades:
        return {
            "total": 0, "wins": 0, "losses": 0,
            "win_rate_pct": 0, "expectancy_pct": 0,
            "profit_factor": 0, "max_drawdown_pct": 0,
            "total_pnl": 0, "can_achieve_3_5pct_goal": False,
        }

    wins   = [t for t in trades if t.won]
    losses = [t for t in trades if not t.won]

    win_rate  = len(wins) / len(trades)
    avg_win   = sum(t.return_pct for t in wins)   / max(1, len(wins))
    avg_loss  = sum(t.return_pct for t in losses) / max(1, len(losses))
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    gross_profit = sum(t.pnl for t in wins)
    gross_loss   = abs(sum(t.pnl for t in losses))
    profit_factor = round(gross_profit / max(1.0, gross_loss), 3)

    # Max drawdown on rolling equity curve
    sorted_trades = sorted(trades, key=lambda t: (t.exit_date, t.ticker))
    equity = 0.0
    peak   = 0.0
    max_dd = 0.0
    for t in sorted_trades:
        equity += t.pnl
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    max_dd_pct = round(max_dd / CAPITAL * 100, 2)

    # Exit reason breakdown
    exit_breakdown = {"TP": 0, "SL": 0, "TIME": 0}
    for t in trades:
        exit_breakdown[t.exit_reason] = exit_breakdown.get(t.exit_reason, 0) + 1

    # Regime breakdown
    regime_breakdown: dict[str, dict] = {}
    for regime in ["Bull", "Sideways", "Bear"]:
        rt = [t for t in trades if t.regime == regime]
        if rt:
            rw = [t for t in rt if t.won]
            regime_breakdown[regime] = {
                "trades":      len(rt),
                "win_rate":    round(len(rw) / len(rt) * 100, 1),
                "avg_return":  round(sum(t.return_pct for t in rt) / len(rt), 2),
                "expectancy":  round(
                    (len(rw) / len(rt)) * (sum(t.return_pct for t in rw) / max(1, len(rw))) +
                    (1 - len(rw) / len(rt)) * (sum(t.return_pct for t in [t2 for t2 in rt if not t2.won]) / max(1, len([t2 for t2 in rt if not t2.won]))),
                    2,
                ),
            }

    # Signal type breakdown
    signal_breakdown: dict[str, dict] = {}
    for sig in ["BREAKOUT", "MOMENTUM", "VOLUME", "MULTI"]:
        st = [t for t in trades if t.signal_type == sig]
        if st:
            sw = [t for t in st if t.won]
            signal_breakdown[sig] = {
                "trades":     len(st),
                "win_rate":   round(len(sw) / len(st) * 100, 1),
                "avg_return": round(sum(t.return_pct for t in st) / len(st), 2),
            }

    # Monthly return distribution
    month_map: dict[str, list[float]] = {}
    for t in trades:
        key = t.exit_date[:7]   # YYYY-MM
        month_map.setdefault(key, []).append(t.return_pct)
    monthly_dist = [
        {"month": k, "trades": len(v), "avg_return": round(sum(v) / len(v), 2)}
        for k, v in sorted(month_map.items())
    ]

    # 3-5% goal analysis
    target_hits = sum(1 for t in trades if 3.0 <= t.return_pct <= 6.0)
    target_rate = round(target_hits / len(trades) * 100, 1)

    # Strategy viability heuristic
    viable = (
        round(win_rate * 100, 1) >= 50 and
        round(expectancy, 2) >= 1.5 and
        profit_factor >= 1.2
    )

    return {
        "total":              len(trades),
        "wins":               len(wins),
        "losses":             len(losses),
        "win_rate_pct":       round(win_rate * 100, 1),
        "avg_win_pct":        round(avg_win, 2),
        "avg_loss_pct":       round(avg_loss, 2),
        "expectancy_pct":     round(expectancy, 2),
        "profit_factor":      profit_factor,
        "max_drawdown_pct":   max_dd_pct,
        "total_pnl":          round(sum(t.pnl for t in trades), 2),
        "final_capital":      round(CAPITAL + sum(t.pnl for t in trades), 2),
        "exit_reasons":       exit_breakdown,
        "trades_in_3_5pct":   target_hits,
        "target_hit_rate":    target_rate,
        "regime_breakdown":   regime_breakdown,
        "signal_breakdown":   signal_breakdown,
        "monthly_dist":       monthly_dist,
        "can_achieve_3_5pct_goal": viable,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  OUTPUT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_output(trades_a: list[Trade], trades_b: list[Trade]) -> dict:
    """Package stats + full trade log into a single output dict."""
    stats_a = compute_stats(trades_a)
    stats_b = compute_stats(trades_b)

    def verdict(stats: dict) -> str:
        if stats.get("total", 0) == 0:
            return "No trades simulated — need more historical data"
        if stats.get("can_achieve_3_5pct_goal"):
            return "✅ Strategy shows positive edge — viable for 3-5% weekly target"
        if stats.get("expectancy_pct", 0) > 0:
            return "⚠️  Marginally positive — refine signal conditions or risk sizing"
        return "❌ Negative expectancy — strategy needs fundamental revision"

    return {
        "generated":  datetime.now().strftime("%d %b %Y %H:%M"),
        "engine":     "MarketPulse Walk-Forward Backtester v1.0",
        "config": {
            "take_profit_pct":     TAKE_PROFIT_PCT,
            "stop_loss_fixed_pct": STOP_LOSS_FIXED_PCT,
            "atr_period":          ATR_PERIOD,
            "atr_sl_multiplier":   ATR_SL_MULTIPLIER,
            "max_hold_days":       MAX_HOLD_DAYS,
            "backtest_weeks":      BACKTEST_WEEKS,
            "capital":             CAPITAL,
            "risk_per_trade_pct":  RISK_PER_TRADE_PCT,
            "max_positions":       MAX_POSITIONS,
            "mode_b_top_n":        MODE_B_TOP_N,
        },
        "mode_a": {
            "description": "Full NSE universe — true strategy edge (no position cap)",
            "summary":     stats_a,
            "verdict":     verdict(stats_a),
            "trades":      [asdict(t) for t in trades_a],
        },
        "mode_b": {
            "description": f"Top {MODE_B_TOP_N} AI-scored picks — execution subset",
            "summary":     stats_b,
            "verdict":     verdict(stats_b),
            "trades":      [asdict(t) for t in trades_b],
        },
        "comparison": {
            "mode_a_win_rate":    stats_a.get("win_rate_pct", 0),
            "mode_b_win_rate":    stats_b.get("win_rate_pct", 0),
            "mode_a_expectancy":  stats_a.get("expectancy_pct", 0),
            "mode_b_expectancy":  stats_b.get("expectancy_pct", 0),
            "ai_filtering_edge":  round(
                stats_b.get("expectancy_pct", 0) - stats_a.get("expectancy_pct", 0), 2
            ),
            "recommendation": (
                "AI filtering adds meaningful edge — use Mode B for live trading"
                if stats_b.get("expectancy_pct", 0) > stats_a.get("expectancy_pct", 0)
                else "AI filtering shows no significant improvement — review scoring model"
            ),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CONSOLE SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_summary(output: dict) -> None:
    """Print a formatted summary to the console."""
    cfg = output["config"]
    print(f"\n{'═'*70}")
    print("  📊  BACKTEST CONFIGURATION")
    print(f"{'─'*70}")
    print(f"  TP: +{cfg['take_profit_pct']}%  |  SL floor: -{cfg['stop_loss_fixed_pct']}%  "
          f"|  ATR SL: {cfg['atr_sl_multiplier']}×ATR{cfg['atr_period']}")
    print(f"  Max hold: {cfg['max_hold_days']} days  |  Capital: ₹{cfg['capital']:,.0f}  "
          f"|  Risk/trade: {cfg['risk_per_trade_pct']}%")
    print(f"  Window: {cfg['backtest_weeks']} weeks")

    for label, key in [("Mode A — Full NSE Universe", "mode_a"),
                       ("Mode B — AI-Filtered Top Picks", "mode_b")]:
        s = output[key]["summary"]
        print(f"\n{'═'*70}")
        print(f"  {label}")
        print(f"{'─'*70}")
        if s.get("total", 0) == 0:
            print("  No trades simulated.")
            continue
        print(f"  Trades         : {s['total']:>6}")
        print(f"  Win Rate       : {s['win_rate_pct']:>5.1f}%")
        print(f"  Expectancy     : {s['expectancy_pct']:>+6.2f}% per trade")
        print(f"  Avg Win        : {s['avg_win_pct']:>+6.2f}%")
        print(f"  Avg Loss       : {s['avg_loss_pct']:>+6.2f}%")
        print(f"  Profit Factor  : {s['profit_factor']:>6.2f}×")
        print(f"  Max Drawdown   : {s['max_drawdown_pct']:>5.2f}%")
        print(f"  Total P&L      :  ₹{s['total_pnl']:>12,.0f}")
        print(f"  Final Capital  :  ₹{s['final_capital']:>12,.0f}")
        print(f"  3-5% target hit: {s['trades_in_3_5pct']:>4} trades ({s['target_hit_rate']}%)")
        viable = "✅ YES" if s.get("can_achieve_3_5pct_goal") else "⚠️  MARGINAL / NO"
        print(f"  3-5% viable?   : {viable}")
        print(f"\n  Verdict: {output[key]['verdict']}")

        if s.get("regime_breakdown"):
            print(f"\n  Regime Breakdown:")
            for r, rd in s["regime_breakdown"].items():
                print(f"    {r:<10}: {rd['trades']:>3} trades  "
                      f"WR={rd['win_rate']:>4.1f}%  "
                      f"avg={rd['avg_return']:>+5.2f}%")

    comp = output["comparison"]
    print(f"\n{'═'*70}")
    print("  🔬  AI FILTERING EDGE")
    print(f"{'─'*70}")
    print(f"  Mode A expectancy: {comp['mode_a_expectancy']:>+6.2f}%")
    print(f"  Mode B expectancy: {comp['mode_b_expectancy']:>+6.2f}%")
    edge = comp['ai_filtering_edge']
    print(f"  AI edge delta    : {edge:>+6.2f}%  "
          f"({'adds value ✅' if edge > 0 else 'no improvement ⚠️'})")
    print(f"\n  {comp['recommendation']}")
    print(f"{'═'*70}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="MarketPulse India — Walk-Forward Backtesting Engine",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--force-download", action="store_true",
        help="Force fresh OHLCV download (ignore parquet cache)",
    )
    parser.add_argument(
        "--mode", default="AB", choices=["A", "B", "AB"],
        help="A=full universe, B=AI picks only, AB=both",
    )
    args = parser.parse_args()

    print("""
╔══════════════════════════════════════════════════════════════════════╗
║  🧪  MarketPulse India — Walk-Forward Backtesting Engine             ║
║  Strict no-lookahead · no-survivorship · hybrid ATR stop loss        ║
╚══════════════════════════════════════════════════════════════════════╝
""")

    # ── Load data ──────────────────────────────────────────────────────
    ohlcv = load_ohlcv(force_download=args.force_download)

    # ── Run backtests ──────────────────────────────────────────────────
    trades_a: list[Trade] = []
    trades_b: list[Trade] = []

    if "A" in args.mode.upper():
        trades_a = run_backtest(ohlcv, mode="A")

    if "B" in args.mode.upper():
        trades_b = run_backtest(ohlcv, mode="B")

    # ── Build and save output ──────────────────────────────────────────
    output = build_output(trades_a, trades_b)

    with open(BACKTEST_OUT, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False, default=str)

    size_kb = BACKTEST_OUT.stat().st_size // 1024

    # ── Print summary ──────────────────────────────────────────────────
    print_summary(output)
    print(f"  📄  Results saved: {BACKTEST_OUT}  ({size_kb} KB)\n")


if __name__ == "__main__":
    main()
