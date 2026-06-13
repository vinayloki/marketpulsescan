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
            opportunities = json.load(f)[:10]  # top 10

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

    # Structure: {timeframe: [{ticker, last_close, return}, ...]}
    performers = all_performers.get(timeframe, [])
    return {
        "timeframe": timeframe,
        "count":     len(performers[:limit]),
        "data":      performers[:limit],
    }
