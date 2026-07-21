"""
calculate_real_rsi_adx.py

Computes exact Wilder's RSI (14) and Wilder's DMI ADX (14) technical indicators
for all stocks in market.json using BSE daily bhavcopy reports.

Strategy:
- Download 60 trading days of BSE bhavcopy CSVs (one per day, all stocks in one file)
- Build a per-symbol OHLCV DataFrame from these daily snapshots
- Compute Wilder RSI(14) and ADX(14) using marketpulse.technical.indicators
- Write the real indicator values back to market.json

Advantages over yfinance:
- No rate limiting: each bhavcopy is a single bulk download for all ~4800 BSE stocks
- Authentic BSE OHLC data (Open, High, Low, Close) from official exchange records
- Much faster: ~60 requests total instead of ~5000+ individual ticker requests
"""

import json
import logging
import pathlib
import sys
import time
import tempfile
from datetime import datetime, timedelta

import pandas as pd
from bse import BSE

# Add pipeline directory to sys.path to import marketpulse.technical.indicators
repo_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "pipeline"))

from marketpulse.technical.indicators import rsi, adx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

MARKET_JSON_PATHS = [
    repo_root / "apps/web/public/api/v1/market.json",
    repo_root / "scan_results/api/v1/market.json",
    repo_root / "pipeline/scan_results/api/v1/market.json",
]

# Number of trading days of history to fetch (need 28+ for RSI(14) warmup)
TRADING_DAYS_TO_FETCH = 60

# Columns in BSE bhavcopy CSV
COL_DATE   = "BizDt"
COL_TICKER = "TckrSymb"
COL_OPEN   = "OpnPric"
COL_HIGH   = "HghPric"
COL_LOW    = "LwPric"
COL_CLOSE  = "ClsPric"
COL_TYPE   = "FinInstrmTp"


def is_trading_day(dt: datetime) -> bool:
    """Return True if dt is a weekday (Mon-Fri). BSE holidays are handled by skipping failed downloads."""
    return dt.weekday() < 5  # 0=Mon, 4=Fri


def get_trading_dates(n_days: int) -> list:
    """Return the last n_days weekdays going backwards from yesterday."""
    dates = []
    dt = datetime.now() - timedelta(days=1)
    while len(dates) < n_days:
        if is_trading_day(dt):
            dates.append(dt)
        dt -= timedelta(days=1)
    return dates


def download_bhavcopy_for_date(bse: BSE, dt: datetime, folder: str) -> pd.DataFrame | None:
    """Download and parse bhavcopy CSV for a given date. Returns None on failure."""
    try:
        path = bse.bhavcopyReport(dt, folder=folder)
        df = pd.read_csv(path)
        # Filter to equity spot market only
        df = df[df[COL_TYPE] == "STK"].copy()
        df[COL_DATE] = pd.to_datetime(dt.date())
        return df[[COL_DATE, COL_TICKER, COL_OPEN, COL_HIGH, COL_LOW, COL_CLOSE]]
    except (RuntimeError, FileNotFoundError, Exception) as exc:
        logging.debug("Skipping %s: %s", dt.strftime("%Y-%m-%d"), exc)
        return None


def main():
    # Find the market.json file
    target_path = None
    for p in MARKET_JSON_PATHS:
        if p.exists():
            target_path = p
            break

    if target_path is None:
        logging.error("market.json not found in any of: %s", MARKET_JSON_PATHS)
        return

    logging.info("Loading market.json from %s", target_path)
    with target_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    stocks = data.get("data", [])
    logging.info("Total stocks in dataset: %d", len(stocks))

    # Build symbol lookup set for fast membership check
    symbol_set = {s["symbol"] for s in stocks}

    # Get list of dates to fetch
    dates = get_trading_dates(TRADING_DAYS_TO_FETCH)
    dates.sort()  # oldest first
    logging.info(
        "Fetching %d bhavcopy reports from %s to %s",
        len(dates),
        dates[0].strftime("%Y-%m-%d"),
        dates[-1].strftime("%Y-%m-%d"),
    )

    # Download all bhavcopy reports and concatenate
    all_frames = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        with BSE(download_folder=tmp_dir) as bse:
            for i, dt in enumerate(dates):
                frame = download_bhavcopy_for_date(bse, dt, tmp_dir)
                if frame is not None:
                    all_frames.append(frame)
                    logging.info("[%d/%d] Downloaded bhavcopy for %s (%d rows)", i + 1, len(dates), dt.strftime("%Y-%m-%d"), len(frame))
                else:
                    logging.info("[%d/%d] Skipped %s (holiday/unavailable)", i + 1, len(dates), dt.strftime("%Y-%m-%d"))
                # Small polite delay between requests
                time.sleep(0.3)

    if not all_frames:
        logging.error("No bhavcopy data downloaded. Aborting.")
        return

    # Combine into single DataFrame
    combined = pd.concat(all_frames, ignore_index=True)
    logging.info("Total combined rows: %d across %d trading days", len(combined), len(all_frames))

    # Sort by ticker and date
    combined.sort_values([COL_TICKER, COL_DATE], inplace=True)

    # Group by ticker and compute RSI + ADX
    updated_count = 0
    skipped_count = 0

    # Build a dict: symbol -> stock entry for O(1) lookup
    symbol_to_stock = {s["symbol"]: s for s in stocks}

    # Group all data by ticker
    grouped = combined.groupby(COL_TICKER)
    available_tickers = set(grouped.groups.keys())

    for stock in stocks:
        sym = stock["symbol"]

        if sym not in available_tickers:
            skipped_count += 1
            continue

        stock_df = grouped.get_group(sym).copy()
        stock_df = stock_df.drop_duplicates(subset=[COL_DATE]).set_index(COL_DATE).sort_index()

        # Need at least 15 bars for RSI(14) and 28 for ADX(14)
        if len(stock_df) < 15:
            skipped_count += 1
            continue

        try:
            close_s = stock_df[COL_CLOSE].astype(float)
            high_s  = stock_df[COL_HIGH].astype(float)
            low_s   = stock_df[COL_LOW].astype(float)

            # Compute exact Wilder's RSI (14)
            rsi_series = rsi(close_s, period=14)
            last_rsi = rsi_series.iloc[-1]
            if pd.isna(last_rsi):
                skipped_count += 1
                continue
            real_rsi = round(float(last_rsi), 1)

            # Compute exact Wilder's DMI ADX (14)
            adx_series, plus_di, minus_di = adx(high_s, low_s, close_s, period=14)
            last_adx = adx_series.iloc[-1]
            if pd.isna(last_adx):
                skipped_count += 1
                continue
            real_adx = round(float(last_adx), 1)

            # Write back into the stock dict
            if "indicators" not in stock or not isinstance(stock.get("indicators"), dict):
                stock["indicators"] = {}

            stock["indicators"]["rsi_14"] = real_rsi
            stock["indicators"]["adx_14"] = real_adx
            updated_count += 1

        except Exception as exc:
            logging.debug("Error computing TA for %s: %s", sym, exc)
            skipped_count += 1

    logging.info(
        "Computed real Wilder RSI(14) & ADX(14) for %d stocks, skipped %d",
        updated_count,
        skipped_count,
    )

    # Save updated market.json to all known paths
    for p in MARKET_JSON_PATHS:
        if p.parent.exists():
            with p.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
            logging.info("Wrote updated indicators to %s", p)

    logging.info("Done!")


if __name__ == "__main__":
    main()
