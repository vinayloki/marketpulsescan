"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — Performance Analytics Engine                           ║
║                                                                              ║
║  Reads:  scan_results/backtest_results.json                                  ║
║  Writes: scan_results/performance_report.json                                ║
║                                                                              ║
║  Metrics computed:                                                           ║
║    - Win rate, avg win, avg loss                                              ║
║    - Expectancy per trade                                                    ║
║    - Profit factor (gross profit / gross loss)                               ║
║    - Max drawdown on equity curve                                            ║
║    - Sharpe-like ratio (weekly returns)                                      ║
║    - Weekly return distribution (histogram buckets)                          ║
║    - Regime-wise performance breakdown                                        ║
║    - Signal-type breakdown                                                   ║
║    - Can the 3-5% weekly goal be achieved?                                   ║
║                                                                              ║
║  Usage:                                                                      ║
║    python performance.py                    # uses default backtest output   ║
║    python performance.py --file my_bt.json  # custom backtest file           ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import json
import logging
import math
import sys
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from config.settings import CAPITAL, OUTPUT_DIR

log = logging.getLogger("performance")

BACKTEST_FILE   = OUTPUT_DIR / "backtest_results.json"
PERFORMANCE_OUT = OUTPUT_DIR / "performance_report.json"


# ══════════════════════════════════════════════════════════════════════════════
#  CORE STATISTICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_equity_curve(trades: list[dict], start_capital: float) -> list[dict]:
    """
    Build a cumulative equity curve from the sorted trade list.
    Returns list of {date, equity, drawdown_pct} dicts for chart rendering.
    """
    sorted_t = sorted(trades, key=lambda t: (t.get("exit_date", ""), t.get("ticker", "")))
    equity   = start_capital
    peak     = start_capital
    curve    = []

    for t in sorted_t:
        equity += t.get("pnl", 0)
        if equity > peak:
            peak = equity
        dd_pct = (peak - equity) / peak * 100 if peak > 0 else 0
        curve.append({
            "date":        t.get("exit_date", ""),
            "ticker":      t.get("ticker", ""),
            "equity":      round(equity, 2),
            "drawdown_pct": round(dd_pct, 2),
        })

    return curve


def compute_max_drawdown(equity_curve: list[dict]) -> tuple[float, float, str, str]:
    """
    Compute max drawdown from equity curve.
    Returns (max_dd_pct, max_dd_abs, peak_date, trough_date).
    """
    if not equity_curve:
        return 0.0, 0.0, "", ""

    peak_eq     = equity_curve[0]["equity"]
    peak_date   = equity_curve[0]["date"]
    max_dd_pct  = 0.0
    max_dd_abs  = 0.0
    trough_date = ""

    for point in equity_curve:
        eq = point["equity"]
        if eq > peak_eq:
            peak_eq   = eq
            peak_date = point["date"]
        dd_abs = peak_eq - eq
        dd_pct = dd_abs / peak_eq * 100 if peak_eq > 0 else 0
        if dd_pct > max_dd_pct:
            max_dd_pct  = dd_pct
            max_dd_abs  = dd_abs
            trough_date = point["date"]

    return round(max_dd_pct, 2), round(max_dd_abs, 2), peak_date, trough_date


def compute_sharpe_like(weekly_returns: list[float], risk_free_weekly: float = 0.0) -> float:
    """
    Sharpe-like ratio using weekly return distribution.
    Annualised: avg_weekly_excess / std_weekly × sqrt(52)
    """
    if len(weekly_returns) < 4:
        return 0.0
    excess = [r - risk_free_weekly for r in weekly_returns]
    avg    = sum(excess) / len(excess)
    var    = sum((r - avg) ** 2 for r in excess) / max(1, len(excess) - 1)
    std    = math.sqrt(var) if var > 0 else 1e-9
    return round(avg / std * math.sqrt(52), 2)


def build_weekly_returns(trades: list[dict]) -> list[float]:
    """Aggregate P&L by exit-week and return a list of weekly return %."""
    week_map: dict[str, float] = {}
    for t in trades:
        date = t.get("exit_date", "")
        if not date:
            continue
        try:
            import datetime
            d = datetime.date.fromisoformat(date)
            iso = f"{d.isocalendar()[0]}-W{d.isocalendar()[1]:02d}"
        except Exception:
            iso = date[:7]
        week_map.setdefault(iso, 0)
        week_map[iso] += t.get("pnl", 0)

    return [pnl / CAPITAL * 100 for pnl in week_map.values()]


def build_return_histogram(returns: list[float], buckets: int = 10) -> list[dict]:
    """
    Build a histogram of per-trade return percentages.
    Returns list of {range_label, count, pct_of_total}.
    """
    if not returns:
        return []

    lo   = min(returns)
    hi   = max(returns)
    span = hi - lo or 1
    step = span / buckets
    hist = []

    for i in range(buckets):
        low  = lo + i * step
        high = lo + (i + 1) * step
        cnt  = sum(1 for r in returns if low <= r < high)
        hist.append({
            "range_low":  round(low, 1),
            "range_high": round(high, 1),
            "label":      f"{low:+.1f}% to {high:+.1f}%",
            "count":      cnt,
            "pct_of_total": round(cnt / len(returns) * 100, 1),
        })

    return hist


def analyse_trades(trades: list[dict], mode: str) -> dict:
    """
    Full performance analysis for a list of trades.
    Returns a comprehensive stats dict for serialisation.
    """
    if not trades:
        return {
            "mode": mode, "total": 0,
            "note": "No trades in this mode — check backtest_results.json",
        }

    wins      = [t for t in trades if t.get("won", False)]
    losses    = [t for t in trades if not t.get("won", False)]
    returns   = [t.get("return_pct", 0) for t in trades]

    n_total   = len(trades)
    n_wins    = len(wins)
    n_losses  = len(losses)
    win_rate  = n_wins / n_total

    avg_win   = sum(t["return_pct"] for t in wins)   / max(1, n_wins)
    avg_loss  = sum(t["return_pct"] for t in losses) / max(1, n_losses)

    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    gross_profit = sum(t.get("pnl", 0) for t in wins)
    gross_loss_  = abs(sum(t.get("pnl", 0) for t in losses))
    profit_factor = gross_profit / max(1.0, gross_loss_)

    total_pnl   = sum(t.get("pnl", 0) for t in trades)
    final_cap   = CAPITAL + total_pnl
    total_ret   = total_pnl / CAPITAL * 100

    # Equity curve + max drawdown
    equity_curve = compute_equity_curve(trades, CAPITAL)
    max_dd_pct, max_dd_abs, peak_dt, trough_dt = compute_max_drawdown(equity_curve)

    # Sharpe-like
    weekly_returns = build_weekly_returns(trades)
    sharpe_like    = compute_sharpe_like(weekly_returns)

    # Exit breakdown
    exit_counts = {"TP": 0, "SL": 0, "TIME": 0}
    for t in trades:
        r = t.get("exit_reason", "TIME")
        exit_counts[r] = exit_counts.get(r, 0) + 1

    avg_hold = sum(t.get("holding_days", 0) for t in trades) / n_total

    # Regime breakdown
    regime_stats: dict[str, dict] = {}
    for regime in ["Bull", "Sideways", "Bear"]:
        rt = [t for t in trades if t.get("regime") == regime]
        if not rt:
            continue
        rw = [t for t in rt if t.get("won")]
        rr = [t["return_pct"] for t in rt]
        regime_stats[regime] = {
            "trades":      len(rt),
            "win_rate_pct": round(len(rw) / len(rt) * 100, 1),
            "avg_return":  round(sum(rr) / len(rr), 2),
            "expectancy":  round(
                (len(rw) / len(rt)) * (sum(t["return_pct"] for t in rw) / max(1, len(rw))) +
                (1 - len(rw) / len(rt)) * (sum(t["return_pct"] for t in [x for x in rt if not x.get("won")]) / max(1, len([x for x in rt if not x.get("won")]))),
                2,
            ),
            "total_pnl": round(sum(t.get("pnl", 0) for t in rt), 2),
        }

    # Signal breakdown
    signal_stats: dict[str, dict] = {}
    for sig in ["BREAKOUT", "MOMENTUM", "VOLUME", "MULTI"]:
        st = [t for t in trades if t.get("signal_type") == sig]
        if not st:
            continue
        sw = [t for t in st if t.get("won")]
        signal_stats[sig] = {
            "trades":      len(st),
            "win_rate_pct": round(len(sw) / len(st) * 100, 1),
            "avg_return":  round(sum(t["return_pct"] for t in st) / len(st), 2),
            "best_trade":  round(max(t["return_pct"] for t in st), 2),
            "worst_trade": round(min(t["return_pct"] for t in st), 2),
        }

    # Monthly distribution
    month_map: dict[str, dict] = {}
    for t in trades:
        key = t.get("exit_date", "")[:7]
        if not key:
            continue
        month_map.setdefault(key, {"pnl": 0, "trades": 0, "wins": 0})
        month_map[key]["pnl"]    += t.get("pnl", 0)
        month_map[key]["trades"] += 1
        if t.get("won"):
            month_map[key]["wins"] += 1

    monthly_dist = [
        {
            "month":     k,
            "trades":    v["trades"],
            "wins":      v["wins"],
            "pnl":       round(v["pnl"], 2),
            "return_pct": round(v["pnl"] / CAPITAL * 100, 2),
            "win_rate":  round(v["wins"] / v["trades"] * 100, 1),
        }
        for k, v in sorted(month_map.items())
    ]

    # Return histogram
    histogram = build_return_histogram(returns)

    # 3-5% goal analysis
    in_target  = sum(1 for r in returns if 3.0 <= r <= 6.0)
    over_target = sum(1 for r in returns if r > 6.0)
    target_rate = round(in_target / n_total * 100, 1)

    # Viability verdict
    viable = win_rate >= 0.50 and expectancy >= 1.5 and profit_factor >= 1.20

    return {
        "mode":                 mode,
        "total_trades":         n_total,
        "wins":                 n_wins,
        "losses":               n_losses,
        # Core metrics
        "win_rate_pct":         round(win_rate * 100, 1),
        "avg_win_pct":          round(avg_win, 2),
        "avg_loss_pct":         round(avg_loss, 2),
        "expectancy_pct":       round(expectancy, 2),
        "profit_factor":        round(profit_factor, 3),
        # Capital
        "total_pnl":            round(total_pnl, 2),
        "final_capital":        round(final_cap, 2),
        "total_return_pct":     round(total_ret, 2),
        # Risk
        "max_drawdown_pct":     max_dd_pct,
        "max_drawdown_abs":     max_dd_abs,
        "max_dd_peak_date":     peak_dt,
        "max_dd_trough_date":   trough_dt,
        # Quality
        "sharpe_like":          sharpe_like,
        "avg_holding_days":     round(avg_hold, 1),
        "exit_reasons":         exit_counts,
        # Goal
        "trades_in_3_5pct":     in_target,
        "trades_over_target":   over_target,
        "target_hit_rate_pct":  target_rate,
        "can_achieve_3_5pct_goal": viable,
        "viability_verdict": (
            "VIABLE — strategy shows consistent edge for 3-5% weekly goal"
            if viable else
            "MARGINAL — refine signal conditions and/or risk sizing"
            if expectancy > 0 else
            "NOT VIABLE — negative expectancy, fundamental revision needed"
        ),
        # Breakdowns (dashboard-ready)
        "regime_breakdown":     regime_stats,
        "signal_breakdown":     signal_stats,
        "monthly_dist":         monthly_dist,
        "return_histogram":     histogram,
        "weekly_returns":       [round(r, 2) for r in weekly_returns],
        # For chart rendering (last 100 equity curve points)
        "equity_curve":         equity_curve[-100:],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CONSOLE PRINT
# ══════════════════════════════════════════════════════════════════════════════

def print_report(data: dict) -> None:
    """Print a rich console summary of the performance report."""
    print(f"\n{'═'*70}")
    print(f"  MarketPulse India — Performance Report")
    print(f"  Generated: {data.get('generated', '—')}")
    print(f"{'═'*70}")

    for mode_key, label in [("mode_a", "Mode A — Full NSE Universe"),
                              ("mode_b", "Mode B — AI-Filtered Picks")]:
        s = data.get(mode_key, {})
        if not s or s.get("total_trades", 0) == 0:
            continue

        print(f"\n  {label}")
        print(f"{'─'*70}")
        print(f"  Trades          : {s['total_trades']:>6}  (wins={s['wins']}, losses={s['losses']})")
        print(f"  Win Rate        : {s['win_rate_pct']:>5.1f}%")
        print(f"  Avg Win         : {s['avg_win_pct']:>+6.2f}%    Avg Loss: {s['avg_loss_pct']:>+6.2f}%")
        print(f"  Expectancy      : {s['expectancy_pct']:>+6.2f}% per trade")
        print(f"  Profit Factor   : {s['profit_factor']:>6.3f}x")
        print(f"  Sharpe-like     : {s['sharpe_like']:>6.2f}")
        print(f"  Max Drawdown    : {s['max_drawdown_pct']:>5.2f}%"
              f"  ({s['max_dd_peak_date']} -> {s['max_dd_trough_date']})")
        print(f"  Total P&L       :  {s['total_pnl']:>+12,.0f}  INR")
        print(f"  Final Capital   :  {s['final_capital']:>+12,.0f}  INR")
        print(f"  Total Return    :  {s['total_return_pct']:>+7.2f}%")
        print(f"  3-5% target     :  {s['trades_in_3_5pct']:>4} trades"
              f"  ({s['target_hit_rate_pct']}% hit rate)")

        verdict_icon = "OK" if s.get("can_achieve_3_5pct_goal") else "NO"
        print(f"\n  [{verdict_icon}] {s.get('viability_verdict', '')}")

        if s.get("regime_breakdown"):
            print(f"\n  Regime Breakdown:")
            for r, rd in s["regime_breakdown"].items():
                print(f"    {r:<10}  {rd['trades']:>3} trades  "
                      f"WR={rd['win_rate_pct']:>4.1f}%  "
                      f"avg={rd['avg_return']:>+5.2f}%  "
                      f"E={rd['expectancy']:>+5.2f}%")

        if s.get("signal_breakdown"):
            print(f"\n  Signal Breakdown:")
            for sig, sd in s["signal_breakdown"].items():
                print(f"    {sig:<12}  {sd['trades']:>4} trades  "
                      f"WR={sd['win_rate_pct']:>4.1f}%  "
                      f"avg={sd['avg_return']:>+5.2f}%")

    cmp = data.get("comparison", {})
    if cmp:
        print(f"\n{'─'*70}")
        print(f"  AI Filtering Edge:")
        print(f"    Mode A expectancy: {cmp.get('mode_a_expectancy', 0):>+6.2f}%")
        print(f"    Mode B expectancy: {cmp.get('mode_b_expectancy', 0):>+6.2f}%")
        print(f"    Delta (AI edge)  : {cmp.get('ai_filtering_edge', 0):>+6.2f}%")

    print(f"\n{'═'*70}\n")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    from datetime import datetime

    parser = argparse.ArgumentParser(
        description="MarketPulse India — Performance Analytics Engine",
    )
    parser.add_argument(
        "--file", default=str(BACKTEST_FILE),
        help="Path to backtest_results.json",
    )
    args = parser.parse_args()

    bt_path = Path(args.file)
    if not bt_path.exists():
        print(f"ERROR: backtest file not found: {bt_path}")
        print("Run backtest.py first.")
        sys.exit(1)

    with open(bt_path, encoding="utf-8") as fh:
        bt = json.load(fh)

    trades_a = bt.get("mode_a", {}).get("trades", [])
    trades_b = bt.get("mode_b", {}).get("trades", [])

    stats_a = analyse_trades(trades_a, "A")
    stats_b = analyse_trades(trades_b, "B")

    output = {
        "generated":    datetime.now().strftime("%d %b %Y %H:%M"),
        "backtest_file": str(bt_path),
        "config":        bt.get("config", {}),
        "mode_a":        stats_a,
        "mode_b":        stats_b,
        "comparison": {
            "mode_a_win_rate":    stats_a.get("win_rate_pct", 0),
            "mode_b_win_rate":    stats_b.get("win_rate_pct", 0),
            "mode_a_expectancy":  stats_a.get("expectancy_pct", 0),
            "mode_b_expectancy":  stats_b.get("expectancy_pct", 0),
            "ai_filtering_edge":  round(
                stats_b.get("expectancy_pct", 0) - stats_a.get("expectancy_pct", 0), 2
            ),
            "mode_a_sharpe":      stats_a.get("sharpe_like", 0),
            "mode_b_sharpe":      stats_b.get("sharpe_like", 0),
            "recommendation": (
                "AI filtering adds meaningful edge — use Mode B for live trading"
                if stats_b.get("expectancy_pct", 0) > stats_a.get("expectancy_pct", 0)
                else "AI filtering shows marginal improvement — review scoring model"
            ),
        },
    }

    with open(PERFORMANCE_OUT, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2, ensure_ascii=False, default=str)

    size_kb = PERFORMANCE_OUT.stat().st_size // 1024
    print_report(output)
    print(f"  Performance report saved: {PERFORMANCE_OUT}  ({size_kb} KB)\n")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
