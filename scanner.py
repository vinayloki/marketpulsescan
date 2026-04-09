"""
╔══════════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — NSE Market Intelligence Engine                     ║
║  (formerly India Swing Trading Scanner)                                  ║
║                                                                          ║
║  Steps 1–5  : Performance scanner (unchanged — existing output files)    ║
║  Steps 6–7  : Opportunity Engine (new — opportunities.json)              ║
║                                                                          ║
║  Zero cost. Fully automated. Runs daily via GitHub Actions.             ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd

# ── MarketPulse modules ───────────────────────────────────────────────────
from config.settings import (
    BATCH_DELAY_SECONDS,
    BATCH_SIZE,
    DOWNLOAD_INTERVAL,
    DOWNLOAD_PERIOD,
    FUNDAMENTALS_TOP_N,
    MIN_DATA_POINTS,
    OUTPUT_DIR,
    SCANNER_LOG,
    TIMEFRAMES,
    TOP_N,
    LOG_FORMAT,
    LOG_DATEFMT,
)
from data_providers import get_provider
from scanners import BreakoutScanner, MomentumScanner, VolumeScanner
from engine import ScoringEngine

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATEFMT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(SCANNER_LOG, mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("scanner")


# ═══════════════════════════════════════════════════════════════════════
#  STEP 1: Fetch NSE Stock Universe
# ═══════════════════════════════════════════════════════════════════════

def fetch_nse_tickers() -> list[str]:
    """
    Fetch all NSE equity tickers via the DataProvider.
    Three-level fallback: NSE CSV → GitHub mirror → disk cache.
    No Node.js required.
    """
    log.info("🔍 Fetching NSE ticker universe...")
    provider = get_provider()
    tickers = provider.fetch_ticker_universe()

    if not tickers:
        log.error("❌ Could not fetch any tickers. Aborting.")
        sys.exit(1)

    log.info(f"📊 Total unique tickers: {len(tickers)}")
    return tickers


# ═══════════════════════════════════════════════════════════════════════
#  STEP 2: Download Historical Price Data (Full OHLCV)
# ═══════════════════════════════════════════════════════════════════════

def download_price_data(tickers: list[str]) -> pd.DataFrame:
    """
    Download full OHLCV (Open, High, Low, Close, Volume) for all tickers.
    Returns a MultiIndex DataFrame: (field, ticker).

    Also derives a Close-only DataFrame for backward compatibility
    with Steps 3–4 performance calculations.
    """
    log.info(
        f"📡 Downloading {DOWNLOAD_PERIOD} OHLCV for "
        f"{len(tickers)} stocks..."
    )
    provider = get_provider()
    ohlcv = provider.fetch_ohlcv(
        tickers,
        period=DOWNLOAD_PERIOD,
        interval=DOWNLOAD_INTERVAL,
    )

    if ohlcv.empty:
        log.error("❌ No price data downloaded. Aborting.")
        sys.exit(1)

    return ohlcv


def extract_close(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """
    Extract the Close level for performance calculations (Steps 3–4).
    Returns a flat DataFrame: columns = tickers, index = dates.
    """
    if "Close" not in ohlcv.columns.get_level_values(0):
        log.error("❌ OHLCV DataFrame missing 'Close' field.")
        sys.exit(1)
    close = ohlcv["Close"].copy()
    # Drop tickers with insufficient data
    valid = [c for c in close.columns
             if close[c].dropna().shape[0] >= MIN_DATA_POINTS]
    return close[valid]


# ═══════════════════════════════════════════════════════════════════════
#  STEP 3: Calculate Multi-Timeframe Performance
# ═══════════════════════════════════════════════════════════════════════

def calculate_performance(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate % change for each stock across all timeframes.
    Unchanged from V1 — same output format.
    """
    log.info("📊 Calculating multi-timeframe performance metrics...")
    results = {}

    for ticker in prices.columns:
        series = prices[ticker].dropna()
        if len(series) < 5:
            continue

        row = {
            "ticker":     ticker,
            "last_close": round(float(series.iloc[-1]), 2),
            "last_date":  str(series.index[-1].date()),
        }

        for tf_name, tf_days in TIMEFRAMES.items():
            if len(series) >= tf_days:
                old_price = float(series.iloc[-tf_days])
                new_price = float(series.iloc[-1])
                if old_price > 0:
                    pct = ((new_price - old_price) / old_price) * 100
                    row[tf_name] = round(pct, 2)
                else:
                    row[tf_name] = None
            else:
                row[tf_name] = None

        results[ticker] = row

    df = pd.DataFrame.from_dict(results, orient="index")
    log.info(
        f"   ✅ Performance calculated for {len(df)} stocks "
        f"across {len(TIMEFRAMES)} timeframes"
    )
    return df


# ═══════════════════════════════════════════════════════════════════════
#  STEP 4: Rank & Export (existing output files — unchanged)
# ═══════════════════════════════════════════════════════════════════════

def rank_and_export(perf_df: pd.DataFrame, mcap_map: dict[str, str]):
    """
    Rank stocks by timeframe and export all existing output files.
    Includes 'm' (Market Cap category) into full_summary.json.
    """
    log.info("🏆 Ranking stocks and exporting results...")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    date_str  = datetime.now().strftime("%d %b %Y")

    # ── Full scan CSV ──────────────────────────────────────────────
    sort_col = "1M" if "1M" in perf_df.columns else "1W"
    perf_sorted = perf_df.sort_values(sort_col, ascending=False, na_position="last")

    csv_path = OUTPUT_DIR / f"full_scan_{timestamp}.csv"
    perf_sorted.to_csv(csv_path, index=False)
    (OUTPUT_DIR / "latest_full_scan.csv").write_bytes(csv_path.read_bytes())
    log.info(f"   📄 Full scan CSV: {csv_path.name}")

    # ── Top performers JSON ────────────────────────────────────────
    top_performers = {}
    for tf in TIMEFRAMES:
        if tf not in perf_df.columns:
            continue
        valid = perf_df.dropna(subset=[tf]).sort_values(tf, ascending=False)
        top_performers[tf] = {
            "top_gainers": valid.head(TOP_N)[["ticker", "last_close", tf]].to_dict("records"),
            "top_losers":  list(reversed(valid.tail(TOP_N)[["ticker", "last_close", tf]].to_dict("records"))),
        }

    tp_path = OUTPUT_DIR / f"top_performers_{timestamp}.json"
    with open(tp_path, "w", encoding="utf-8") as f:
        json.dump(top_performers, f, indent=2, ensure_ascii=False)
    latest_tp = OUTPUT_DIR / "latest_top_performers.json"
    with open(latest_tp, "w", encoding="utf-8") as f:
        json.dump(top_performers, f, indent=2, ensure_ascii=False)
    log.info(f"   📄 Top performers JSON: {tp_path.name}")

    # ── Summary JSON (for dashboard stats row) ─────────────────────
    summary = {
        "scan_date":           date_str,
        "scan_timestamp":      timestamp,
        "total_stocks_scanned": len(perf_df),
        "timeframes":          list(TIMEFRAMES.keys()),
        "market_breadth":      {},
        "top_10_by_timeframe": {},
    }
    for tf in TIMEFRAMES:
        if tf not in perf_df.columns:
            continue
        col = perf_df[tf].dropna()
        summary["market_breadth"][tf] = {
            "advancing":           int((col > 0).sum()),
            "declining":           int((col < 0).sum()),
            "unchanged":           int((col == 0).sum()),
            "advance_decline_ratio": round(int((col > 0).sum()) / max(int((col < 0).sum()), 1), 2),
            "avg_return_pct":      round(float(col.mean()), 2),
            "median_return_pct":   round(float(col.median()), 2),
        }
        top10 = perf_df.dropna(subset=[tf]).nlargest(10, tf)
        summary["top_10_by_timeframe"][tf] = (
            top10[["ticker", "last_close", tf]].to_dict("records")
        )

    summary_path = OUTPUT_DIR / "latest_scan_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log.info(f"   📄 Summary JSON: {summary_path.name}")

    # ── Full summary JSON (compact — for browser table) ────────────
    full_records = []
    for _, row in perf_sorted.iterrows():
        record = {
            "t": row["ticker"], 
            "c": row["last_close"], 
            "d": row["last_date"],
            "m": mcap_map.get(row["ticker"], "S")
        }
        for tf in TIMEFRAMES:
            if tf in perf_df.columns:
                val = row.get(tf)
                record[tf] = (
                    round(float(val), 2)
                    if val is not None and not pd.isna(val)
                    else None
                )
        full_records.append(record)

    full_summary_path = OUTPUT_DIR / "full_summary.json"
    with open(full_summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {"generated": date_str, "stocks": full_records},
            f, separators=(",", ":"), ensure_ascii=False,
        )
    log.info(f"   📄 Full summary JSON: {full_summary_path.name} ({len(full_records)} stocks)")

    # ── Console summary ────────────────────────────────────────────
    print("\n" + "═" * 70)
    print(f"  📊 SCAN COMPLETE — {date_str}")
    print(f"  Stocks scanned: {len(perf_df)}")
    print("═" * 70)
    for tf in TIMEFRAMES:
        if tf not in summary.get("market_breadth", {}):
            continue
        mb = summary["market_breadth"][tf]
        print(f"\n  ⏱️  {tf}: ▲ {mb['advancing']} · ▼ {mb['declining']} · A/D {mb['advance_decline_ratio']}")
        if tf in summary.get("top_10_by_timeframe", {}):
            top3 = summary["top_10_by_timeframe"][tf][:3]
            print(f"     🏆 " + ", ".join(
                f"{s['ticker']} ({s[tf]:+.1f}%)" for s in top3
            ))
    print("\n" + "═" * 70)


# ═══════════════════════════════════════════════════════════════════════
#  STEP 5: Fetch Fundamentals for Top Movers
# ═══════════════════════════════════════════════════════════════════════

def fetch_fundamentals(perf_df: pd.DataFrame) -> dict[str, dict]:
    """
    Fetch fundamental data for top movers across all timeframes.
    Returns dict for use by both Step 4 (existing) and Step 6 (engine).
    """
    log.info("🔬 Fetching fundamentals for top movers...")
    provider = get_provider()

    # Collect top movers across all timeframes
    top_symbols = set()
    for tf in TIMEFRAMES:
        if tf not in perf_df.columns:
            continue
        valid = perf_df.dropna(subset=[tf])
        top = valid.nlargest(TOP_N, tf).index.tolist()
        top_symbols.update(top)
        if "ticker" in perf_df.columns:
            top_symbols.update(valid.nlargest(TOP_N, tf)["ticker"].tolist())

    top_list = sorted(list(top_symbols))[:FUNDAMENTALS_TOP_N]
    fundamentals = provider.fetch_fundamentals(top_list)

    # Save standalone fundamentals.json (existing format)
    fund_list = list(fundamentals.values())
    fund_path = OUTPUT_DIR / "fundamentals.json"
    with open(fund_path, "w", encoding="utf-8") as f:
        json.dump(
            {"generated": datetime.now().strftime("%d %b %Y"),
             "count": len(fund_list), "stocks": fund_list},
            f, separators=(",", ":"), ensure_ascii=False,
        )
    log.info(f"   📄 Fundamentals JSON saved: {fund_path.name}")
    return fundamentals


# ═══════════════════════════════════════════════════════════════════════
#  STEP 6: Run Opportunity Engine (NEW)
# ═══════════════════════════════════════════════════════════════════════

def run_opportunity_engine(ohlcv: pd.DataFrame, fundamentals: dict[str, dict]):
    """
    Run all three scanners on the full OHLCV dataset,
    fuse their signals, rank by score, and write opportunities.json.
    """
    log.info("🎯 Running Opportunity Engine...")

    # ── Run all scanners ────────────────────────────────────────────
    scanners = [BreakoutScanner(), VolumeScanner(), MomentumScanner()]
    scanner_results: dict[str, dict] = {}

    for scanner in scanners:
        log.info(f"   ⚡ Running {scanner.NAME}...")
        scanner_results[scanner.NAME] = scanner.scan(ohlcv)

    total_signals = sum(len(v) for v in scanner_results.values())
    log.info(f"   📊 Total raw signals: {total_signals}")

    # ── Fuse and rank ───────────────────────────────────────────────
    engine = ScoringEngine()
    opportunities = engine.fuse(scanner_results, fundamentals)

    # ── Save output ─────────────────────────────────────────────────
    engine.save(opportunities)

    # ── Console summary ─────────────────────────────────────────────
    print("\n" + "═" * 70)
    print(f"  🎯 OPPORTUNITY ENGINE — {len(opportunities)} ranked setups")
    print("═" * 70)
    for opp in opportunities[:5]:
        signals_str = " · ".join(opp.signals)
        print(f"  #{opp.rank:>3}  {opp.ticker:<15} Score: {opp.score:>3}  [{signals_str}]")
    if len(opportunities) > 5:
        print(f"  ... and {len(opportunities) - 5} more in opportunities.json")
    print("═" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def main():
    start = time.time()

    print("""
╔══════════════════════════════════════════════════════════════════╗
║  🇮🇳  MarketPulse India — Daily NSE Intelligence Engine          ║
║  Performance · Breakout · Volume · Momentum · Opportunities     ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    # Step 1: Ticker universe (now via Python, no Node.js)
    tickers = fetch_nse_tickers()

    # Step 2: Full OHLCV download
    ohlcv = download_price_data(tickers)
    prices = extract_close(ohlcv)  # Close-only view for Steps 3–4

    # Step 3: Multi-timeframe performance
    performance = calculate_performance(prices)

    # Step 4: Rank and export (existing output files)
    provider = get_provider()
    mcap_map = getattr(provider, "fetch_mcap_categories", lambda: {})()
    rank_and_export(performance, mcap_map)

    # Step 5: Fundamentals for top movers
    fundamentals = fetch_fundamentals(performance)

    # Step 6: Opportunity Engine (new)
    run_opportunity_engine(ohlcv, fundamentals)

    elapsed = time.time() - start
    log.info(f"⏱️  Total time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
