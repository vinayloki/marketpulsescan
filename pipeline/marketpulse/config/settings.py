"""
MarketPulseScan — Central Configuration

Port of legacy config/settings.py. All constants in one place.
Environment variables override defaults for CI / GitHub Actions.
"""

from __future__ import annotations

import os
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
# In the monorepo layout, the pipeline package lives at <repo>/pipeline/
# so ROOT_DIR is the repo root (two levels up from this file).
_PKG_DIR = Path(__file__).parent.parent  # pipeline/marketpulse/
PIPELINE_DIR = _PKG_DIR.parent  # pipeline/
ROOT_DIR = PIPELINE_DIR.parent  # repo root

# Writable output dirs — created on import
CACHE_DIR = Path(os.getenv("MPS_CACHE_DIR", str(ROOT_DIR / "cache")))
OUTPUT_DIR = Path(os.getenv("MPS_OUTPUT_DIR", str(ROOT_DIR / "scan_results")))
SCHEMA_DIR = ROOT_DIR / "schemas" / "v1"

CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Data Branch ───────────────────────────────────────────────────────────────
DATA_BRANCH = os.getenv("MPS_DATA_BRANCH", "data")
STAGING_API_PATH = "api/v1/staging"
PRODUCTION_API_PATH = "api/v1"

# ── Ticker Universe ───────────────────────────────────────────────────────────
NSE_EQUITY_CSV_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_EQUITY_MIRROR_URL = (
    "https://raw.githubusercontent.com/pkjmesra/PKScreener/"
    "actions-data-download/results/Indices/EQUITY_L.csv"
)
NSE_SYMBOLS_CACHE = CACHE_DIR / "nse_symbols.json"
UNIVERSE_CACHE_TTL_H: float = 12.0  # re-fetch universe every 12h

# ── Download Settings ─────────────────────────────────────────────────────────
DOWNLOAD_PERIOD: str = "5y"  # yfinance period string
DOWNLOAD_INTERVAL: str = "1d"  # daily candles
BATCH_SIZE: int = 15  # tickers per yfinance batch
BATCH_DELAY_SECONDS: float = 6.0  # polite delay between batches
MIN_DATA_POINTS: int = 30  # drop ticker if fewer rows

# ── OHLCV Cache ───────────────────────────────────────────────────────────────
OHLCV_CACHE_FILE = CACHE_DIR / "ohlcv_backtest.parquet"
OHLCV_CACHE_MAX_AGE_H: float = 24.0

# ── Performance Timeframes ────────────────────────────────────────────────────
TIMEFRAMES: dict[str, str] = {
    "1W": "1W",
    "2W": "2W",
    "1M": "1M",
    "3M": "3M",
    "6M": "6M",
    "12M": "12M",
}
TOP_N: int = 20

# ── Scanner Thresholds ────────────────────────────────────────────────────────
BREAKOUT_PROXIMITY_PCT: float = 2.0
BREAKOUT_VOLUME_MULT: float = 1.5
VOLUME_SPIKE_MULT: float = 2.5
VOLUME_SPIKE_MAX_MULT: float = 6.0

# ── EMA / RSI ─────────────────────────────────────────────────────────────────
EMA_FAST: int = 9
EMA_MID: int = 21
EMA_SLOW: int = 50
RSI_PERIOD: int = 14
RSI_MOMENTUM_LOW: int = 50
RSI_MOMENTUM_HIGH: int = 75

# ── Scoring ───────────────────────────────────────────────────────────────────
SCORE_WEIGHTS: dict[str, int] = {
    "breakout": 30,
    "volume": 25,
    "momentum": 45,
}
MULTI_SIGNAL_BONUS: dict[int, int] = {2: 5, 3: 10}
MIN_SCORE_THRESHOLD: int = 25
MAX_OPPORTUNITIES: int = 100

# ── Fundamentals ──────────────────────────────────────────────────────────────
FUNDAMENTALS_TOP_N: int = 100
FUNDAMENTALS_WORKERS: int = 1

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
LOG_DATEFMT = "%H:%M:%S"
SCANNER_LOG = OUTPUT_DIR / "scanner.log"

# ── Backtesting ───────────────────────────────────────────────────────────────
BACKTEST_WEEKS: int = 260
TAKE_PROFIT_PCT: float = 4.0
STOP_LOSS_FIXED_PCT: float = 2.0
ATR_PERIOD: int = 14
ATR_SL_MULTIPLIER: float = 1.5
MAX_HOLD_DAYS: int = 5
MODE_B_TOP_N: int = 20

# ── Risk Management ───────────────────────────────────────────────────────────
CAPITAL: int = int(os.getenv("MPS_CAPITAL", "1000000"))  # Rs 10L default
RISK_PER_TRADE_PCT: float = 1.5
MAX_POSITIONS: int = 5
MAX_SECTOR_EXPOSURE_PCT: float = 30.0
WEEKLY_DRAWDOWN_CAP_PCT: float = 5.0

# ── Market Regime ─────────────────────────────────────────────────────────────
NIFTY_SYMBOL: str = "^NSEI"
REGIME_EMA_PERIOD: int = 200
REGIME_SIDEWAYS_BAND_PCT: float = 3.0
REGIME_BULL_MIN_SCORE: int = 25
REGIME_SIDEWAYS_MIN_SCORE: int = 55
REGIME_BEAR_MIN_SCORE: int = 75
REGIME_BULL_SIZE_MULT: float = 1.0
REGIME_SIDEWAYS_SIZE_MULT: float = 0.5
REGIME_BEAR_SIZE_MULT: float = 0.25

# ── News ──────────────────────────────────────────────────────────────────────
NEWS_LOOKBACK_HOURS: int = 36
NEWS_FEEDS: dict[str, str] = {
    "Livemint Markets": "https://www.livemint.com/rss/markets",
    "Economic Times Stocks": (
        "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms"
    ),
    "RBI Press Releases": "https://rbi.org.in/Scripts/RSS.aspx",
}
