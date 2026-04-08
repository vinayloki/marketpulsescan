"""
╔══════════════════════════════════════════════════════════════════════╗
║  INDIA SWING TRADING SCANNER — DAILY NSE STOCK SCANNER             ║
║  Scans all NSE-listed stocks and ranks by multi-timeframe momentum ║
║  Timeframes: 1W, 2W, 1M, 3M, 6M, 12M                             ║
║  Data Source: Yahoo Finance (free, no API key)                     ║
║  Schedule: Run once daily after 4:00 PM IST                       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import json
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import yfinance as yf
import requests

# ─── Configuration ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "scan_results"
OUTPUT_DIR.mkdir(exist_ok=True)

# Timeframes in approximate trading days
TIMEFRAMES = {
    "1W":  5,
    "2W":  10,
    "1M":  21,
    "3M":  63,
    "6M":  126,
    "12M": 252,
}

# How many top performers to include in each timeframe ranking
TOP_N = 20

# yfinance download period (must cover 12 months + buffer)
DOWNLOAD_PERIOD = "13mo"

# Batch size for yfinance downloads (to avoid rate limits)
BATCH_SIZE = 50
BATCH_DELAY_SECONDS = 2

# ─── Logging ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(OUTPUT_DIR / "scanner.log", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger("scanner")


# ═══════════════════════════════════════════════════════════════════
#  STEP 1: Fetch the NSE Stock Universe
# ═══════════════════════════════════════════════════════════════════

import subprocess

def fetch_nse_tickers() -> list[str]:
    """
    Fetch all NSE equity tickers.
    Uses the Node.js stock-nse-india package as the official source.
    """
    log.info("🔍 Fetching official symbols from NSE API via stock-nse-india (Node.js)...")
    
    node_script = SCRIPT_DIR / "nse_fetcher.js"
    json_output = OUTPUT_DIR / "nse_symbols.json"
    
    try:
        # Run the Node script
        result = subprocess.run(
            ["node", str(node_script)],
            cwd=str(SCRIPT_DIR),
            capture_output=True,
            text=True,
            check=True
        )
        if result.stdout:
            log.info(f"   ℹ️  Node output: {result.stdout.strip()}")
            
        # Read the generated JSON
        if json_output.exists():
            with open(json_output, "r", encoding="utf-8") as f:
                tickers = json.load(f)
            
            # Additional cleanup
            tickers = [t.strip().upper() for t in tickers if t.strip() and not t.strip().isdigit()]
            tickers = sorted(list(set(tickers)))
            
            # For testing and avoiding IP blocks on bulk downloads, we will keep the universe to a manageable size.
            # However, the user asked to scan all NSE stocks. yfinance handles thousands fine, but we'll limit to 1000 
            # to be safe for memory, or use everything. We will use everything since user wants everything.
            log.info(f"📊 Total unique tickers to scan: {len(tickers)}")
            return tickers
        else:
            log.error("   ❌ Node script completed but no JSON output file found.")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        log.error(f"   ❌ Node script failed: {e.stderr}")
        sys.exit(1)
    except Exception as e:
        log.error(f"   ❌ Failed to fetch symbols via Node: {e}")
        sys.exit(1)


# ═══════════════════════════════════════════════════════════════════
#  STEP 2: Download Historical Price Data
# ═══════════════════════════════════════════════════════════════════

def download_price_data(tickers: list[str]) -> pd.DataFrame:
    """
    Download closing price history for all tickers using yfinance.
    Downloads in batches to respect rate limits.
    Returns a DataFrame with dates as index and tickers as columns.
    """
    log.info(f"📡 Downloading {DOWNLOAD_PERIOD} of price data for {len(tickers)} stocks...")

    # Append .NS suffix for NSE tickers
    yf_tickers = [f"{t}.NS" for t in tickers]

    all_data = pd.DataFrame()
    total_batches = (len(yf_tickers) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(yf_tickers), BATCH_SIZE):
        batch = yf_tickers[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        log.info(f"   📦 Batch {batch_num}/{total_batches} — downloading {len(batch)} stocks...")

        try:
            data = yf.download(
                tickers=batch,
                period=DOWNLOAD_PERIOD,
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )

            if not data.empty:
                # Extract Close prices
                if len(batch) == 1:
                    # Single ticker returns flat columns
                    close = data[["Close"]].rename(columns={"Close": batch[0]})
                else:
                    # Multi-ticker returns multi-level columns
                    close = data.xs("Close", level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data[["Close"]]

                if all_data.empty:
                    all_data = close
                else:
                    all_data = all_data.join(close, how="outer")

        except Exception as e:
            log.warning(f"   ⚠️  Batch {batch_num} failed: {e}")

        # Rate limit protection
        if batch_num < total_batches:
            time.sleep(BATCH_DELAY_SECONDS)

    # Clean column names (remove .NS suffix)
    all_data.columns = [str(c).replace(".NS", "") for c in all_data.columns]

    # Drop tickers with insufficient data (< 10 data points)
    min_data_points = 10
    valid_cols = [c for c in all_data.columns if all_data[c].dropna().shape[0] >= min_data_points]
    all_data = all_data[valid_cols]

    log.info(f"   ✅ Downloaded data for {len(all_data.columns)} stocks ({len(all_data)} trading days)")
    return all_data


# ═══════════════════════════════════════════════════════════════════
#  STEP 3: Calculate Multi-Timeframe Performance
# ═══════════════════════════════════════════════════════════════════

def calculate_performance(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate percentage change for each stock across all timeframes.
    Returns a DataFrame with tickers as rows and timeframes as columns.
    """
    log.info("📊 Calculating multi-timeframe performance metrics...")

    results = {}
    latest_prices = prices.iloc[-1]

    for ticker in prices.columns:
        series = prices[ticker].dropna()
        if len(series) < 5:
            continue

        row = {
            "ticker": ticker,
            "last_close": round(float(series.iloc[-1]), 2),
            "last_date": str(series.index[-1].date()),
        }

        for tf_name, tf_days in TIMEFRAMES.items():
            if len(series) >= tf_days:
                old_price = float(series.iloc[-tf_days])
                new_price = float(series.iloc[-1])
                if old_price > 0:
                    pct_change = ((new_price - old_price) / old_price) * 100
                    row[tf_name] = round(pct_change, 2)
                else:
                    row[tf_name] = None
            else:
                row[tf_name] = None

        results[ticker] = row

    df = pd.DataFrame.from_dict(results, orient="index")
    log.info(f"   ✅ Calculated performance for {len(df)} stocks across {len(TIMEFRAMES)} timeframes")
    return df


# ═══════════════════════════════════════════════════════════════════
#  STEP 4: Rank & Export Results
# ═══════════════════════════════════════════════════════════════════

def rank_and_export(perf_df: pd.DataFrame):
    """
    Rank stocks by each timeframe and export results.
    Generates:
      1. Full scan CSV (all stocks, all timeframes)
      2. Top performers JSON (top N per timeframe)
      3. Summary JSON for dashboard integration
    """
    log.info("🏆 Ranking stocks and exporting results...")
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    date_str = datetime.now().strftime("%d %b %Y")

    # ── 1. Full scan CSV ──
    csv_path = OUTPUT_DIR / f"full_scan_{timestamp}.csv"
    # Sort by 1M performance by default
    sort_col = "1M" if "1M" in perf_df.columns else "1W"
    perf_df_sorted = perf_df.sort_values(by=sort_col, ascending=False, na_position="last")
    perf_df_sorted.to_csv(csv_path, index=False)
    log.info(f"   📄 Full scan CSV saved: {csv_path.name}")

    # ── 2. Top performers per timeframe ──
    top_performers = {}
    for tf_name in TIMEFRAMES.keys():
        if tf_name not in perf_df.columns:
            continue
        valid = perf_df.dropna(subset=[tf_name]).sort_values(by=tf_name, ascending=False)
        top = valid.head(TOP_N)[["ticker", "last_close", tf_name]].to_dict(orient="records")
        bottom = valid.tail(TOP_N)[["ticker", "last_close", tf_name]].to_dict(orient="records")
        top_performers[tf_name] = {
            "top_gainers": top,
            "top_losers": list(reversed(bottom)),
        }

    top_json_path = OUTPUT_DIR / f"top_performers_{timestamp}.json"
    with open(top_json_path, "w", encoding="utf-8") as f:
        json.dump(top_performers, f, indent=2, ensure_ascii=False)
    log.info(f"   📄 Top performers JSON saved: {top_json_path.name}")

    # ── 3. Summary JSON for dashboard ──
    summary = {
        "scan_date": date_str,
        "scan_timestamp": timestamp,
        "total_stocks_scanned": len(perf_df),
        "timeframes": list(TIMEFRAMES.keys()),
        "market_breadth": {},
        "top_10_by_timeframe": {},
    }

    for tf_name in TIMEFRAMES.keys():
        if tf_name not in perf_df.columns:
            continue
        col = perf_df[tf_name].dropna()
        advancing = int((col > 0).sum())
        declining = int((col < 0).sum())
        unchanged = int((col == 0).sum())

        summary["market_breadth"][tf_name] = {
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "advance_decline_ratio": round(advancing / max(declining, 1), 2),
            "avg_return_pct": round(float(col.mean()), 2),
            "median_return_pct": round(float(col.median()), 2),
        }

        # Top 10 for dashboard
        top10 = perf_df.dropna(subset=[tf_name]).nlargest(10, tf_name)
        summary["top_10_by_timeframe"][tf_name] = top10[["ticker", "last_close", tf_name]].to_dict(orient="records")

    summary_path = OUTPUT_DIR / "latest_scan_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    log.info(f"   📄 Summary JSON saved: {summary_path.name}")

    # ── 4. Also save as 'latest' for easy access ──
    latest_csv = OUTPUT_DIR / "latest_full_scan.csv"
    perf_df_sorted.to_csv(latest_csv, index=False)
    latest_top = OUTPUT_DIR / "latest_top_performers.json"
    with open(latest_top, "w", encoding="utf-8") as f:
        json.dump(top_performers, f, indent=2, ensure_ascii=False)
    log.info(f"   📄 Latest files updated ✅")

    # ── 5. Full summary JSON for browser table (compact — no raw prices) ──
    full_summary_records = []
    for _, row in perf_df_sorted.iterrows():
        record = {
            "t": row["ticker"],
            "c": row["last_close"],
            "d": row["last_date"],
        }
        for tf in TIMEFRAMES.keys():
            if tf in perf_df.columns:
                val = row.get(tf)
                record[tf] = round(float(val), 2) if val is not None and not pd.isna(val) else None
        full_summary_records.append(record)

    full_summary_path = OUTPUT_DIR / "full_summary.json"
    with open(full_summary_path, "w", encoding="utf-8") as f:
        json.dump({"generated": date_str, "stocks": full_summary_records}, f, separators=(",", ":"), ensure_ascii=False)
    log.info(f"   📄 Full summary JSON saved: {full_summary_path.name} ({len(full_summary_records)} stocks)")

    # ── Print summary to console ──
    print("\n" + "═" * 70)
    print(f"  📊 SCAN COMPLETE — {date_str}")
    print(f"  Total Stocks Scanned: {len(perf_df)}")
    print("═" * 70)

    for tf_name in TIMEFRAMES.keys():
        if tf_name not in summary.get("market_breadth", {}):
            continue
        mb = summary["market_breadth"][tf_name]
        print(f"\n  ⏱️  {tf_name} Performance:")
        print(f"     Advancing: {mb['advancing']}  |  Declining: {mb['declining']}  |  A/D Ratio: {mb['advance_decline_ratio']}")
        print(f"     Avg Return: {mb['avg_return_pct']}%  |  Median: {mb['median_return_pct']}%")

        if tf_name in summary.get("top_10_by_timeframe", {}):
            top3 = summary["top_10_by_timeframe"][tf_name][:3]
            top3_str = ", ".join([f"{s['ticker']} ({s[tf_name]:+.1f}%)" for s in top3])
            print(f"     🏆 Top 3: {top3_str}")

    print("\n" + "═" * 70)
    print(f"  📁 Results saved to: {OUTPUT_DIR}")
    print("═" * 70 + "\n")


# ═══════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    start_time = time.time()

    print("""
╔══════════════════════════════════════════════════════════════════╗
║       🇮🇳 INDIA SWING TRADING SCANNER — DAILY NSE SCAN          ║
║       Timeframes: 1W · 2W · 1M · 3M · 6M · 12M                ║
╚══════════════════════════════════════════════════════════════════╝
    """)

    # Step 1: Get ticker universe
    tickers = fetch_nse_tickers()

    # Step 2: Download price data
    prices = download_price_data(tickers)

    if prices.empty:
        log.error("❌ No price data was downloaded. Check internet connection or yfinance.")
        sys.exit(1)

    # Step 3: Calculate performance
    performance = calculate_performance(prices)

    # Step 4: Rank and export
    rank_and_export(performance)

    elapsed = time.time() - start_time
    log.info(f"⏱️  Total scan time: {elapsed:.1f} seconds")


if __name__ == "__main__":
    main()
