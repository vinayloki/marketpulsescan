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

# ─── Performance Timeframes ─────────────────────────────────────────
# Expressed as pandas DateOffset strings.
# Anchoring method: for each timeframe we find the last available close
# ON OR BEFORE (scan_date - offset), matching TradingView's calendar logic.
# 1W  = Monday of the current ISO week
# 2W  = Monday two weeks ago
# 1M+ = same calendar day N months/years ago
TIMEFRAMES = {
    "1W":  "1W",
    "2W":  "2W",
    "1M":  "1M",
    "3M":  "3M",
    "6M":  "6M",
    "12M": "12M",
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

# ═════════════════════════════════════════════════════════════════════
#  BACKTESTING ENGINE
# ═════════════════════════════════════════════════════════════════════

# Walk-forward window — how many historical weeks to simulate
BACKTEST_WEEKS          = 52       # 1 full year of Mondays

# Exit levels (configurable — change to test different setups)
TAKE_PROFIT_PCT         = 4.0      # +4% → TP hit → WIN
STOP_LOSS_FIXED_PCT     = 2.0      # floor: SL never tighter than -2%

# Hybrid SL = max(STOP_LOSS_FIXED_PCT, ATR_SL_MULTIPLIER × ATR)
ATR_PERIOD              = 14       # look-back for Average True Range
ATR_SL_MULTIPLIER       = 1.5      # SL = 1.5 × ATR14 (if wider than 2%)

# Time-based exit: exit at close of the Nth bar after entry
MAX_HOLD_DAYS           = 5        # ≈ 1 trading week

# Top N picks for Mode B (AI-filtered subset)
MODE_B_TOP_N            = 20

# Parquet cache for fast OHLCV reloads (avoids repeated 2100-stock download)
OHLCV_CACHE_FILE        = CACHE_DIR / "ohlcv_backtest.parquet"
OHLCV_CACHE_MAX_AGE_H   = 24       # hours before cache is considered stale

# ═════════════════════════════════════════════════════════════════════
#  RISK MANAGEMENT
# ═════════════════════════════════════════════════════════════════════

# Starting capital — set this to YOUR actual trading capital (₹)
CAPITAL                 = 1_000_000   # ₹ 10 Lakh default

# Risk per trade as % of total capital
# qty = (CAPITAL × RISK_PER_TRADE_PCT / 100) / stop_loss_distance
RISK_PER_TRADE_PCT      = 1.5         # risk ₹15,000 per trade on ₹10L capital

# Portfolio-level controls
MAX_POSITIONS           = 5           # max concurrent open positions
MAX_SECTOR_EXPOSURE_PCT = 30          # max % of capital in any one sector
WEEKLY_DRAWDOWN_CAP_PCT = 5.0         # halt new trades if weekly DD > 5%

# ═════════════════════════════════════════════════════════════════════
#  MARKET REGIME FILTER
# ═════════════════════════════════════════════════════════════════════

# yfinance symbol for NIFTY 50 index (no .NS suffix for indices)
NIFTY_SYMBOL            = "^NSEI"

# EMA period used to classify market regime
REGIME_EMA_PERIOD       = 200

# ±band around EMA200 that defines "Sideways" (% from EMA200)
# Outside this band: Bull (above) or Bear (below)
REGIME_SIDEWAYS_BAND_PCT = 3.0

# Minimum AI score to accept a trade signal in each regime
REGIME_BULL_MIN_SCORE      = 25    # all qualified signals active
REGIME_SIDEWAYS_MIN_SCORE  = 55    # only high-confidence in sideways
REGIME_BEAR_MIN_SCORE      = 75    # only highest conviction in bear

# Sizing multipliers applied per regime (fraction of normal position)
REGIME_BULL_SIZE_MULT      = 1.0
REGIME_SIDEWAYS_SIZE_MULT  = 0.5
REGIME_BEAR_SIZE_MULT      = 0.25

