"""
╔══════════════════════════════════════════════════════════════════════╗
║  MarketPulse India — Central Configuration                          ║
║  All constants in one place. Edit here to tune the engine.         ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────────
ROOT_DIR        = Path(__file__).parent.parent.resolve()
OUTPUT_DIR      = ROOT_DIR / "scan_results"
CACHE_DIR       = ROOT_DIR / "cache"

OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ─── Ticker Universe ─────────────────────────────────────────────────
# Primary: live NSE equity list CSV
NSE_EQUITY_CSV_URL = (
    "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
)
# Fallback 1: PKScreener's daily-cached mirror (same file, very reliable)
NSE_EQUITY_MIRROR_URL = (
    "https://raw.githubusercontent.com/pkjmesra/PKScreener/"
    "actions-data-download/results/Indices/EQUITY_L.csv"
)
# Fallback 2: local disk cache written on each successful fetch
NSE_SYMBOLS_CACHE = OUTPUT_DIR / "nse_symbols.json"

# ─── Download Settings ───────────────────────────────────────────────
DOWNLOAD_PERIOD       = "13mo"   # yfinance period string
DOWNLOAD_INTERVAL     = "1d"     # daily candles
BATCH_SIZE            = 50       # tickers per yfinance batch
BATCH_DELAY_SECONDS   = 2        # polite delay between batches
MIN_DATA_POINTS       = 30       # drop ticker if fewer rows than this

# ─── Performance Timeframes (in trading days) ────────────────────────
TIMEFRAMES = {
    "1W":  5,
    "2W":  10,
    "1M":  21,
    "3M":  63,
    "6M":  126,
    "12M": 252,
}
TOP_N = 20  # top/bottom N per timeframe in ranked output

# ─── Scanner Thresholds ──────────────────────────────────────────────
# 52-Week Breakout
BREAKOUT_PROXIMITY_PCT   = 2.0   # within X% of 52W high
BREAKOUT_VOLUME_MULT     = 1.5   # volume must be >= X × 20D avg

# Volume Spike
VOLUME_SPIKE_MULT        = 2.5   # volume spike threshold (× 20D avg)
VOLUME_SPIKE_MAX_MULT    = 6.0   # cap for normalising score

# EMA + RSI Momentum
EMA_FAST, EMA_MID, EMA_SLOW = 9, 21, 50
RSI_PERIOD               = 14
RSI_MOMENTUM_LOW         = 50    # below this = no signal
RSI_MOMENTUM_HIGH        = 75    # above this = overbought, exclude

# ─── Scoring & Ranking ───────────────────────────────────────────────
SCORE_WEIGHTS = {
    "breakout": 30,   # max 30 pts
    "volume":   25,   # max 25 pts
    "momentum": 45,   # max 45 pts
}
MULTI_SIGNAL_BONUS = {2: 5, 3: 10}   # bonus for 2 or 3 signals
MIN_SCORE_THRESHOLD = 25              # minimum score to appear in output
MAX_OPPORTUNITIES   = 100             # top N in opportunities.json

# ─── Fundamentals ────────────────────────────────────────────────────
FUNDAMENTALS_TOP_N      = 100    # fetch fundamentals for top N movers
FUNDAMENTALS_WORKERS    = 10     # parallel threads for yfinance .info

# ─── Logging ─────────────────────────────────────────────────────────
LOG_FORMAT    = "%(asctime)s │ %(levelname)-7s │ %(message)s"
LOG_DATEFMT   = "%H:%M:%S"
SCANNER_LOG   = OUTPUT_DIR / "scanner.log"
