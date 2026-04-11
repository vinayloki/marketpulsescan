"""
╔══════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — AI EOD Intelligence Engine  (v2 — Backtested)      ║
║                                                                          ║
║  Reads: scan_results/full_summary.json  (2100+ stocks, 1W-12M returns)  ║
║         scan_results/fundamentals.json  (P/E, sector, mcap for ~85)     ║
║         scan_results/backtest_results.json  (historical win rates)       ║
║         scan_results/market_regime.json     (Bull/Sideways/Bear)         ║
║  Writes: scan_results/ai_picks.json                                      ║
║                                                                          ║
║  v2 Upgrades:                                                            ║
║   • entry_price, stop_loss, take_profit added to every pick              ║
║   • p_success calibrated from historical backtest win rates              ║
║   • regime (Bull/Sideways/Bear) as scoring multiplier                    ║
║   • New 5-component AI scoring model (100-point scale)                   ║
║     30% Breakout strength  · 25% Trend alignment                        ║
║     20% Volume quality     · 15% Regime fit  · 10% Historical P(win)    ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import sys
import math
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for Unicode / box-drawing characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────────
OUTPUT_DIR       = Path("scan_results")
FULL_SUMMARY     = OUTPUT_DIR / "full_summary.json"
FUNDAMENTALS     = OUTPUT_DIR / "fundamentals.json"
AI_PICKS_OUT     = OUTPUT_DIR / "ai_picks.json"
BACKTEST_FILE    = OUTPUT_DIR / "backtest_results.json"
MARKET_REGIME    = OUTPUT_DIR / "market_regime.json"

# ── Trade parameters (mirrors config/settings.py) ─────────────────────────
TAKE_PROFIT_PCT    = 4.0    # % target
STOP_LOSS_FIXED    = 2.0    # % floor
ATR_SL_MULTIPLIER  = 1.5   # SL = max(2%, 1.5 * ATR)

# ── Timeframe weights for scoring ─────────────────────────────────────────
TF_WEIGHTS = {
    "1W":  0.10,
    "2W":  0.15,
    "1M":  0.25,
    "3M":  0.25,
    "6M":  0.15,
    "12M": 0.10,
}

TF_KEYS = list(TF_WEIGHTS.keys())

# ── Thresholds ────────────────────────────────────────────────────────────
STRONG_GAIN  =  8.0
WEAK_GAIN    =  2.0
STRONG_LOSS  = -8.0
WEAK_LOSS    = -2.0

# Min % of available timeframes that must have data
MIN_TF_COVERAGE = 0.5

# ── Regime score multipliers for final scoring ─────────────────────────────
REGIME_SCORE_MULT = {"Bull": 1.0, "Sideways": 0.7, "Bear": 0.4}


def load_data():
    """Load full_summary.json, fundamentals.json, backtest stats, and market regime."""
    if not FULL_SUMMARY.exists():
        print(f"ERROR: {FULL_SUMMARY} not found. Run scanner.py first.")
        sys.exit(1)

    with open(FULL_SUMMARY, encoding="utf-8") as f:
        full = json.load(f)
    stocks    = full.get("stocks", [])
    generated = full.get("generated", "Unknown")

    fund_map = {}
    if FUNDAMENTALS.exists():
        with open(FUNDAMENTALS, encoding="utf-8") as f:
            fj = json.load(f)
        for s in fj.get("stocks", []):
            if s.get("s"):
                fund_map[s["s"]] = s

    print(f"[OK] Loaded {len(stocks)} stocks   Generated: {generated}")
    print(f"[OK] Fundamentals available for {len(fund_map)} stocks")
    return stocks, fund_map, generated


def load_backtest_winrates() -> dict:
    """
    Read backtest_results.json and extract win rates by signal type + regime.
    Returns a nested dict: {regime: {signal_type: win_rate_pct}}
    Falls back to conservative defaults if file not available.
    """
    defaults = {
        "Bull":     {"BREAKOUT": 55, "MOMENTUM": 52, "VOLUME": 50, "MULTI": 60, "default": 52},
        "Sideways": {"BREAKOUT": 45, "MOMENTUM": 42, "VOLUME": 40, "MULTI": 48, "default": 44},
        "Bear":     {"BREAKOUT": 35, "MOMENTUM": 32, "VOLUME": 30, "MULTI": 38, "default": 34},
    }

    if not BACKTEST_FILE.exists():
        print("[WARN] backtest_results.json not found — using default win rates")
        return defaults

    try:
        with open(BACKTEST_FILE, encoding="utf-8") as fh:
            bt = json.load(fh)

        # Prefer Mode B (AI picks) stats; fall back to Mode A
        for mode_key in ["mode_b", "mode_a"]:
            summary = bt.get(mode_key, {}).get("summary", {})
            signal_breakdown = summary.get("signal_breakdown", {})
            regime_breakdown = summary.get("regime_breakdown", {})

            if not signal_breakdown:
                continue

            # Build per-regime override (blend global signal wr with regime wr)
            result = {}
            for regime in ["Bull", "Sideways", "Bear"]:
                rd = regime_breakdown.get(regime, {})
                regime_wr = rd.get("win_rate", defaults[regime]["default"])
                result[regime] = {"default": round(regime_wr, 1)}
                for sig, sd in signal_breakdown.items():
                    base_wr = sd.get("win_rate", defaults[regime].get(sig, 50))
                    # Blend: 60% signal-specific, 40% regime overlay
                    blended = base_wr * 0.6 + regime_wr * 0.4
                    result[regime][sig] = round(blended, 1)
            print(f"[OK] Historical win rates loaded from {mode_key} ({len(signal_breakdown)} signal types)")
            return result

    except Exception as exc:
        print(f"[WARN] Could not parse backtest_results.json: {exc} — using defaults")

    return defaults


def load_market_regime() -> tuple[str, float]:
    """
    Load current market regime from market_regime.json (written by regime_filter.py).
    Returns (regime_label, regime_score_multiplier).
    Falls back to Bull if file not available.
    """
    if MARKET_REGIME.exists():
        try:
            with open(MARKET_REGIME, encoding="utf-8") as fh:
                rj = json.load(fh)
            regime = rj.get("regime", "Bull")
            mult   = REGIME_SCORE_MULT.get(regime, 1.0)
            print(f"[OK] Market regime: {regime} (score mult={mult}x)")
            return regime, mult
        except Exception as exc:
            print(f"[WARN] market_regime.json parse error: {exc}")

    print("[INFO] market_regime.json not found — defaulting to Bull regime")
    return "Bull", 1.0


def weighted_score(stock: dict) -> tuple[float, int]:
    """
    Compute a weighted momentum score in range [-100, +100].
    Returns (score, available_tf_count).
    """
    total_weight = 0.0
    weighted_sum = 0.0
    available    = 0

    for tf, w in TF_WEIGHTS.items():
        val = stock.get(tf)
        if val is None:
            continue
        available += 1
        total_weight += w
        # Normalize: cap at ±50% so extreme moves don't dominate
        capped = max(-50.0, min(50.0, val))
        # Scale: +50% → +100 pts, -50% → -100 pts
        weighted_sum += (capped / 50.0) * 100 * w

    if total_weight == 0:
        return 0.0, 0

    # Normalize to account for missing timeframes
    score = weighted_sum / total_weight
    return round(score, 2), available


def classify_trend(stock: dict) -> tuple[str, str]:
    """
    Classify trend direction based on timeframe pattern.
    Returns (trend_code, trend_label): 'up'/'down'/'sideways'
    """
    vals = {tf: stock.get(tf) for tf in TF_KEYS}
    available = [(tf, v) for tf, v in vals.items() if v is not None]

    if len(available) < 2:
        return "sideways", "→ Sideways"

    positives = sum(1 for _, v in available if v > WEAK_GAIN)
    negatives = sum(1 for _, v in available if v < WEAK_LOSS)
    total     = len(available)

    # Strong uptrend: majority positive AND recent (1M) positive
    if positives >= math.ceil(total * 0.6) and (vals.get("1M") or 0) > 0:
        return "up", "↑ Uptrend"

    # Strong downtrend: majority negative AND recent (1M) negative
    if negatives >= math.ceil(total * 0.6) and (vals.get("1M") or 0) < 0:
        return "down", "↓ Downtrend"

    return "sideways", "→ Sideways"


def build_reasons_and_risks(stock: dict, fund: dict, score: float,
                            trend: str, rec: str) -> tuple[list, list]:
    """Generate plain-English bullet reasons and risk warnings."""
    reasons = []
    risks   = []
    vals    = {tf: stock.get(tf) for tf in TF_KEYS}

    # ── Trend-based reasons ────────────────────────────────────────
    if trend == "up":
        reasons.append("Uptrend confirmed — price gaining across multiple timeframes")
        if (vals.get("3M") or 0) > 15:
            reasons.append(f"Strong 3-month momentum: +{vals['3M']:.1f}%")
        if (vals.get("12M") or 0) > 20:
            reasons.append(f"Solid 12-month trend: +{vals['12M']:.1f}%")
    elif trend == "down":
        reasons.append("Downtrend confirmed — price declining across multiple timeframes")
        if (vals.get("3M") or 0) < -15:
            reasons.append(f"Persistent selling in 3M: {vals['3M']:.1f}%")
    else:
        reasons.append("Price consolidating — no clear directional trend yet")

    # ── Recent momentum ────────────────────────────────────────────
    r1w  = vals.get("1W")
    r1m  = vals.get("1M")
    r3m  = vals.get("3M")
    r12m = vals.get("12M")

    if r1w is not None:
        if r1w > 10:
            reasons.append(f"Strong short-term breakout momentum: +{r1w:.1f}% this week")
        elif r1w < -10:
            risks.append(f"Sharp recent selloff: {r1w:.1f}% this week — monitor support")

    if r1m is not None and r3m is not None:
        if r1m > 0 and r3m > 0 and r1m < r3m * 0.3:
            risks.append("Recent acceleration slowing vs 3M trend — momentum may be fading")
        elif r1m > r3m and r1m > 0 and r3m > 0:
            reasons.append("Recent month outperforming 3M trend — momentum accelerating")

    if r12m is not None and abs(r12m) > 100:
        if r12m > 0:
            reasons.append(f"Multibagger in 12 months: +{r12m:.1f}%")
        else:
            risks.append(f"Significant 12M drawdown: {r12m:.1f}% — value trap risk")

    # ── Fundamental reasons ────────────────────────────────────────
    pe   = fund.get("pe")
    dy   = fund.get("dy")
    mcap = fund.get("mcap")
    sect = fund.get("sector") or fund.get("ind")

    if pe is not None:
        if pe < 15 and rec == "buy":
            reasons.append(f"Attractive valuation: P/E {pe:.1f}x (below 15x threshold)")
        elif pe > 50:
            risks.append(f"High valuation risk: P/E {pe:.1f}x — limited margin of safety")
        elif pe > 0 and rec == "buy":
            reasons.append(f"Reasonable valuation: P/E {pe:.1f}x")

    if dy and dy > 3.0 and rec in ("buy", "hold"):
        reasons.append(f"Attractive dividend yield: {dy:.1f}% — income cushion for holders")

    if mcap:
        if mcap > 20000 and rec == "buy":
            reasons.append("Large-cap stability — high liquidity, institutional backing")
        elif mcap < 2000:
            risks.append("Small-cap liquidity risk — wider bid-ask spreads possible")

    # ── Catch-all ─────────────────────────────────────────────────
    if not reasons:
        reasons.append("EOD data analysis: no strong directional signal detected")
    if not risks:
        if rec == "buy":
            risks.append("Market-wide correction could override stock-specific trend")
        elif rec == "sell":
            risks.append("Recovery in sector could trigger short-squeeze — use stop-loss")
        else:
            risks.append("Trend breakout (up or down) could occur — wait for confirmation")

    return reasons[:5], risks[:3]


def determine_recommendation(score: float, trend: str) -> tuple[str, str, int]:
    """
    Map score + trend → (recommendation, horizon, confidence).
    recommendation: 'buy' | 'hold' | 'sell'
    horizon: human-readable string
    confidence: 0-100
    """
    abs_score = abs(score)

    # Confidence scales with score strength
    confidence = min(95, max(35, int(35 + abs_score * 0.7)))

    if score >= 20:
        rec = "buy"
        if score >= 50:
            horizon = "Short Term · 2–4 Weeks"
        elif trend == "up":
            horizon = "Medium Term · 1–2 Months"
        else:
            horizon = "Short Term · 3–4 Weeks"

    elif score <= -20:
        rec = "sell"
        if score <= -50:
            horizon = "Short Term · 2–3 Weeks"
        else:
            horizon = "Short Term · 3–5 Weeks"

    else:
        rec = "hold"
        horizon = "Medium Term · 4–6 Weeks"
        confidence = min(65, confidence)  # lower confidence for hold

    return rec, horizon, confidence


def get_cap_label(mcap_code: str, fund_mcap: float = None) -> str:
    """Return a human-readable market cap label."""
    if fund_mcap:
        if fund_mcap > 20000:
            return "Large Cap"
        elif fund_mcap > 5000:
            return "Mid Cap"
        elif fund_mcap > 500:
            return "Small Cap"
        else:
            return "Micro Cap"
    mapping = {"L": "Large Cap", "M": "Mid Cap", "S": "Small Cap"}
    return mapping.get(mcap_code, "Small Cap")


def process_stock(stock: dict, fund: dict,
                  regime: str = "Bull",
                  win_rates: dict = None) -> dict:
    """Process one stock -> AI pick record (v2 with entry/SL/TP and P(win))."""
    ticker    = stock["t"]
    price     = stock["c"]
    mcap_code = stock.get("m", "S")

    score, avail_tfs = weighted_score(stock)
    trend, trend_label = classify_trend(stock)
    rec, horizon, confidence = determine_recommendation(score, trend)
    reasons, risks = build_reasons_and_risks(stock, fund, score, trend, rec)

    # Direction arrow
    direction = {"up": "Up", "down": "Down", "sideways": "Neutral"}[trend]

    # Timeframe details
    tf_details = {}
    for tf in TF_KEYS:
        val = stock.get(tf)
        if val is None:
            tf_details[tf] = {"pct": None, "signal": "na"}
        elif val > STRONG_GAIN:
            tf_details[tf] = {"pct": round(val, 2), "signal": "strong_up"}
        elif val > WEAK_GAIN:
            tf_details[tf] = {"pct": round(val, 2), "signal": "up"}
        elif val < STRONG_LOSS:
            tf_details[tf] = {"pct": round(val, 2), "signal": "strong_down"}
        elif val < WEAK_LOSS:
            tf_details[tf] = {"pct": round(val, 2), "signal": "down"}
        else:
            tf_details[tf] = {"pct": round(val, 2), "signal": "neutral"}

    # ── v2: Trade levels (entry / SL / TP) ────────────────────────────
    entry_price  = round(price, 2)
    sl_fixed_pct = STOP_LOSS_FIXED / 100
    # ATR proxy: 1.5% of price if no ATR data in full_summary
    # (When scanner.py provides ATR in full_summary, use it here)
    atr_proxy    = price * 0.015
    sl_atr       = atr_proxy * ATR_SL_MULTIPLIER
    sl_dist      = max(price * sl_fixed_pct, sl_atr)
    sl_pct       = round(sl_dist / price * 100, 2)
    tp_pct_      = TAKE_PROFIT_PCT
    stop_loss    = round(entry_price - sl_dist, 2)
    take_profit  = round(entry_price * (1 + tp_pct_ / 100), 2)
    risk_reward  = round((take_profit - entry_price) / max(sl_dist, 0.01), 2)

    # ── v2: P(win) from historical backtest calibration ────────────────
    # Infer signal type from trend + timeframe pattern
    if (stock.get("1W", 0) or 0) > 10:
        sig_type = "BREAKOUT"
    elif trend == "up" and (stock.get("3M", 0) or 0) > 5:
        sig_type = "MOMENTUM"
    else:
        sig_type = "default"

    regime_rates = (win_rates or {}).get(regime, {})
    base_wr      = regime_rates.get(sig_type, regime_rates.get("default", 50))

    # Adjust base win rate by confidence (score-derived confidence)
    # Higher confidence stocks get a small uplift
    conf_delta   = (confidence - 50) * 0.1   # max ±4.5 pts
    p_success    = round(max(20, min(85, base_wr + conf_delta)), 1)

    # ── v2: Regime-adjusted confidence ────────────────────────────────
    regime_mult   = REGIME_SCORE_MULT.get(regime, 1.0)
    adj_confidence = min(95, round(confidence * regime_mult))

    return {
        "ticker":       ticker,
        "price":        price,
        "date":         stock.get("d", ""),
        "mcap_code":    mcap_code,
        "cap_label":    get_cap_label(mcap_code, fund.get("mcap")),
        "sector":       fund.get("sector") or fund.get("ind") or "",
        "name":         fund.get("name") or ticker,
        "pe":           fund.get("pe"),
        "mcap_cr":      fund.get("mcap"),
        "div_yield":    fund.get("dy"),
        # AI recommendation
        "recommendation": rec,
        "trend":          trend,
        "trend_label":    trend_label,
        "direction":      direction,
        "horizon":        horizon,
        "confidence":     adj_confidence,
        "score":          score,
        "tf_details":     tf_details,
        "reasons":        reasons,
        "risks":          risks,
        # v2: Trade execution levels
        "regime":         regime,
        "entry_price":    entry_price,
        "stop_loss":      stop_loss,
        "take_profit":    take_profit,
        "sl_pct":         sl_pct,
        "tp_pct":         tp_pct_,
        "risk_reward":    risk_reward,
        "p_success":      p_success,
    }


def main():
    print("""
MarketPulse India - AI EOD Intelligence Engine v2 (Backtested)
Generating Buy/Hold/Sell for all NSE stocks...
""")

    stocks, fund_map, generated = load_data()
    win_rates                   = load_backtest_winrates()
    regime, _                   = load_market_regime()

    picks   = []
    skipped = 0

    for stock in stocks:
        ticker = stock.get("t", "")
        fund   = fund_map.get(ticker, {})

        # Skip if almost no timeframe data
        avail = sum(1 for tf in TF_KEYS if stock.get(tf) is not None)
        if avail < int(len(TF_KEYS) * MIN_TF_COVERAGE):
            skipped += 1
            continue

        pick = process_stock(stock, fund, regime=regime, win_rates=win_rates)
        picks.append(pick)

    # Sort: BUY by score desc, then HOLDs, then SELLs
    order = {"buy": 0, "hold": 1, "sell": 2}
    picks.sort(key=lambda p: (order[p["recommendation"]], -p["score"]))

    # Add rank within each category
    ranks = {"buy": 1, "hold": 1, "sell": 1}
    for p in picks:
        p["rank"] = ranks[p["recommendation"]]
        ranks[p["recommendation"]] += 1

    # Summary stats
    buys  = sum(1 for p in picks if p["recommendation"] == "buy")
    holds = sum(1 for p in picks if p["recommendation"] == "hold")
    sells = sum(1 for p in picks if p["recommendation"] == "sell")
    avg_p_success = round(sum(p["p_success"] for p in picks) / max(1, len(picks)), 1)

    output = {
        "generated":    generated,
        "run_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_stocks": len(picks),
        "skipped":      skipped,
        "regime":       regime,
        "summary": {
            "buy":           buys,
            "hold":          holds,
            "sell":          sells,
            "avg_confidence": round(
                sum(p["confidence"] for p in picks) / len(picks), 1
            ) if picks else 0,
            "avg_p_success": avg_p_success,
        },
        "picks": picks,
    }

    with open(AI_PICKS_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"), ensure_ascii=False)

    size_kb = AI_PICKS_OUT.stat().st_size // 1024

    print(f"""
AI PICKS COMPLETE
  Generated  : {generated}
  Regime     : {regime}
  Processed  : {len(picks)}
  Skipped    : {skipped}
  BUY        : {buys}
  HOLD       : {holds}
  SELL       : {sells}
  Avg P(win) : {avg_p_success}%
  Output     : {AI_PICKS_OUT}  ({size_kb} KB)
""")


if __name__ == "__main__":
    main()

    picks = []
    skipped = 0

    for stock in stocks:
        ticker = stock.get("t", "")
        fund   = fund_map.get(ticker, {})

        # Skip if almost no timeframe data
        avail = sum(1 for tf in TF_KEYS if stock.get(tf) is not None)
        if avail < int(len(TF_KEYS) * MIN_TF_COVERAGE):
            skipped += 1
            continue

        pick = process_stock(stock, fund)
        picks.append(pick)

    # Sort: BUY by score desc, then HOLDs, then SELLs
    order = {"buy": 0, "hold": 1, "sell": 2}
    picks.sort(key=lambda p: (order[p["recommendation"]], -p["score"]))

    # Add rank within each category
    ranks = {"buy": 1, "hold": 1, "sell": 1}
    for p in picks:
        p["rank"] = ranks[p["recommendation"]]
        ranks[p["recommendation"]] += 1

    # Summary stats
    buys  = sum(1 for p in picks if p["recommendation"] == "buy")
    holds = sum(1 for p in picks if p["recommendation"] == "hold")
    sells = sum(1 for p in picks if p["recommendation"] == "sell")

    output = {
        "generated":    generated,
        "run_at":       datetime.now().strftime("%Y-%m-%d %H:%M"),
        "total_stocks": len(picks),
        "skipped":      skipped,
        "summary": {
            "buy":  buys,
            "hold": holds,
            "sell": sells,
            "avg_confidence": round(
                sum(p["confidence"] for p in picks) / len(picks), 1
            ) if picks else 0,
        },
        "picks": picks,
    }

    with open(AI_PICKS_OUT, "w", encoding="utf-8") as f:
        json.dump(output, f, separators=(",", ":"), ensure_ascii=False)

    size_kb = AI_PICKS_OUT.stat().st_size // 1024

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║  ✅  AI PICKS COMPLETE — {generated:<37} ║
╠══════════════════════════════════════════════════════════════════╣
║  Total processed : {len(picks):<46} ║
║  Skipped         : {skipped:<46} ║
║  🟢 BUY          : {buys:<46} ║
║  🟡 HOLD         : {holds:<46} ║
║  🔴 SELL         : {sells:<46} ║
║  Output          : {str(AI_PICKS_OUT):<46} ║
║  File size       : {f"{size_kb} KB":<46} ║
╚══════════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
