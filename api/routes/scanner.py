import csv
import json
import os
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import ScanResult, Stock

router = APIRouter()

SCAN_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "scan_results")


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — multi-timeframe
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stage2")
def get_stage2_candidates(
    timeframe: str = Query("daily", enum=["daily", "weekly", "monthly"]),
    limit: int = Query(200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    """Retrieve Stage 2 stocks for a given timeframe, ordered by composite score."""
    results = (
        db.query(ScanResult)
        .filter(ScanResult.stage == "Stage 2", ScanResult.timeframe == timeframe)
        .order_by(ScanResult.composite_score.desc())
        .limit(limit)
        .all()
    )

    output = []
    for r in results:
        stock = db.query(Stock).filter(Stock.symbol == r.symbol).first()
        output.append({
            "symbol":      r.symbol,
            "name":        stock.name   if stock else r.symbol,
            "sector":      stock.sector if stock else "Unknown",
            "exchange":    stock.exchange if stock else "NSE",
            "score":       r.composite_score,
            "rs_rating":   r.rs_score,
            "price":       r.d_close,
            "sma_fast":    r.d_ema50,
            "sma_mid":     r.d_ema150,
            "sma_slow":    r.d_ema200,
            "high_52w":    r.high_52w,
            "low_52w":     r.low_52w,
            "above_fast":  r.price_above_50,
            "above_mid":   r.price_above_150,
            "above_slow":  r.price_above_200,
            "ma_aligned":  r.ema50_above_200,
            "ma_rising":   r.ema200_rising,
            "timeframe":   r.timeframe,
            "updated_at":  r.updated_at.isoformat() if r.updated_at else None,
        })

    return {"timeframe": timeframe, "count": len(output), "data": output}


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard summary — reads live JSON files from scan_results/
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Return high-level scanner summary for the Dashboard page."""

    # --- market regime -------------------------------------------------------
    regime_data = {}
    regime_path = os.path.join(SCAN_RESULTS_DIR, "market_regime.json")
    if os.path.exists(regime_path):
        with open(regime_path) as f:
            regime_data = json.load(f)

    # --- scan summary (breadth + top 10 per timeframe) ----------------------
    summary_data = {}
    summary_path = os.path.join(SCAN_RESULTS_DIR, "latest_scan_summary.json")
    if os.path.exists(summary_path):
        with open(summary_path) as f:
            summary_data = json.load(f)

    # --- opportunities -------------------------------------------------------
    opportunities = []
    opp_path = os.path.join(SCAN_RESULTS_DIR, "opportunities.json")
    if os.path.exists(opp_path):
        with open(opp_path) as f:
            opp_data = json.load(f)
            opportunities = opp_data.get("opportunities", [])[:10]  # top 10

    # --- Stage 2 counts per timeframe from DB --------------------------------
    stage2_counts = {}
    for tf in ("daily", "weekly", "monthly"):
        count = (
            db.query(ScanResult)
            .filter(ScanResult.stage == "Stage 2", ScanResult.timeframe == tf)
            .count()
        )
        stage2_counts[tf] = count

    return {
        "market_regime":  regime_data,
        "scan_summary":   summary_data,
        "opportunities":  opportunities,
        "stage2_counts":  stage2_counts,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Top performers — reads from JSON files
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/top-performers")
def get_top_performers(
    timeframe: str = Query("1M", enum=["1W", "2W", "1M", "3M", "6M", "12M"]),
    limit: int = Query(20, ge=1, le=100),
):
    """Return top-performing stocks from the latest scan by return timeframe."""
    path = os.path.join(SCAN_RESULTS_DIR, "latest_top_performers.json")
    if not os.path.exists(path):
        return {"timeframe": timeframe, "count": 0, "data": []}

    with open(path) as f:
        all_performers = json.load(f)

    # Structure: {timeframe: {"top_gainers": [...], "top_losers": [...]}}
    timeframe_data = all_performers.get(timeframe, {})
    performers = timeframe_data.get("top_gainers", [])
    
    return {
        "timeframe": timeframe,
        "count":     len(performers[:limit]),
        "data":      performers[:limit],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Full Market Scan — ALL NSE/BSE stocks from latest_full_scan.csv
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/market")
def get_market_scan(
    sort_by: str  = Query("1M",  enum=["1W", "2W", "1M", "3M", "6M", "12M", "last_close"]),
    order:   str  = Query("desc", enum=["asc", "desc"]),
    sector:  str  = Query(""),
    mcap:    str  = Query("", enum=["", "L", "M", "S"]),
    limit:   int  = Query(500, ge=1, le=3500),
    offset:  int  = Query(0, ge=0),
):
    """
    Return all NSE+BSE stocks from latest_full_scan.csv joined with
    fundamentals for sector/name/mcap data.
    Supports sorting by any return column, and filtering by sector + mcap.
    """
    csv_path  = os.path.join(SCAN_RESULTS_DIR, "latest_full_scan.csv")
    fund_path = os.path.join(SCAN_RESULTS_DIR, "fundamentals.json")

    if not os.path.exists(csv_path):
        return {"count": 0, "total": 0, "data": []}

    # Build fundamentals lookup {symbol -> record}
    fund_lookup = {}
    if os.path.exists(fund_path):
        with open(fund_path) as f:
            fund_data = json.load(f)
        for s in fund_data.get("stocks", []):
            sym = s.get("s", "")
            fund_lookup[sym] = s
            # also index without .NS / .BO suffix
            base = sym.replace(".NS", "").replace(".BO", "")
            fund_lookup[base] = s

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker", "")
            base   = ticker.replace(".NS", "").replace(".BO", "")
            fund   = fund_lookup.get(ticker) or fund_lookup.get(base) or {}

            row_sector   = fund.get("sector", "")
            row_mcap_code = fund.get("mcap_code", "")

            # Apply filters
            if sector and sector.lower() not in (row_sector or "").lower():
                continue
            if mcap and row_mcap_code != mcap:
                continue

            def _f(k):
                try: return float(row.get(k) or 0)
                except: return 0.0

            rows.append({
                "ticker":    ticker,
                "symbol":    base,
                "name":      fund.get("name", base),
                "sector":    row_sector,
                "mcap_code": row_mcap_code,
                "mcap_cr":   fund.get("mcap"),
                "exchange":  "BSE" if ".BO" in ticker else "NSE",
                "price":     _f("last_close"),
                "last_date": row.get("last_date", ""),
                "ret_1w":    _f("1W"),
                "ret_2w":    _f("2W"),
                "ret_1m":    _f("1M"),
                "ret_3m":    _f("3M"),
                "ret_6m":    _f("6M"),
                "ret_12m":   _f("12M"),
            })

    # Sort
    sort_col_map = {
        "1W": "ret_1w", "2W": "ret_2w", "1M": "ret_1m",
        "3M": "ret_3m", "6M": "ret_6m", "12M": "ret_12m",
        "last_close": "price",
    }
    sort_col = sort_col_map.get(sort_by, "ret_1m")
    rows.sort(key=lambda r: r.get(sort_col) or 0, reverse=(order == "desc"))

    total = len(rows)
    return {
        "total":  total,
        "count":  len(rows[offset: offset + limit]),
        "data":   rows[offset: offset + limit],
    }
