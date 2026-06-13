"""
export_static_api.py
====================
Exports DB + JSON scan results to flat static JSON files under scan_results/api/.
These files power the GitHub Pages frontend without needing a live FastAPI server.

IMPORTANT: This script intentionally does NOT import FastAPI so that it can run
in the GitHub Actions CI environment which does not install the full server stack.
All query logic is inlined directly here.
"""

import csv
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("export_static_api")

SCAN_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "scan_results")
API_EXPORT_DIR   = os.path.join(SCAN_RESULTS_DIR, "api")
os.makedirs(API_EXPORT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_json(path, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Could not load {path}: {e}")
    return default


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    log.info(f"  ✅ Written → {os.path.relpath(path)}")


# ─────────────────────────────────────────────────────────────────────────────
# Export: /api/summary  (dashboard summary — no DB needed, pure JSON files)
# ─────────────────────────────────────────────────────────────────────────────

def export_summary():
    regime_data  = _load_json(os.path.join(SCAN_RESULTS_DIR, "market_regime.json"))
    summary_data = _load_json(os.path.join(SCAN_RESULTS_DIR, "latest_scan_summary.json"))
    opp_data     = _load_json(os.path.join(SCAN_RESULTS_DIR, "opportunities.json"))
    opportunities = opp_data.get("opportunities", [])[:10]

    # Stage 2 counts — read from the scan summary if available, else default 0
    stage2_counts = summary_data.get("stage2_counts", {"daily": 0, "weekly": 0, "monthly": 0})

    payload = {
        "market_regime": regime_data,
        "scan_summary":  summary_data,
        "opportunities": opportunities,
        "stage2_counts": stage2_counts,
    }
    _write_json(os.path.join(API_EXPORT_DIR, "summary.json"), payload)


# ─────────────────────────────────────────────────────────────────────────────
# Export: /api/top-performers_{tf}  (from latest_top_performers.json)
# ─────────────────────────────────────────────────────────────────────────────

def export_top_performers():
    path = os.path.join(SCAN_RESULTS_DIR, "latest_top_performers.json")
    all_performers = _load_json(path, default={})

    for tf in ["1W", "2W", "1M", "3M", "6M", "12M"]:
        timeframe_data = all_performers.get(tf, {})
        performers     = timeframe_data.get("top_gainers", [])
        payload = {
            "timeframe": tf,
            "count":     len(performers[:10]),
            "data":      performers[:10],
        }
        _write_json(os.path.join(API_EXPORT_DIR, f"top-performers_{tf}.json"), payload)


# ─────────────────────────────────────────────────────────────────────────────
# Export: /api/stage2_{tf}  (from DB via SQLAlchemy — optional, skip if DB missing)
# ─────────────────────────────────────────────────────────────────────────────

def export_stage2():
    try:
        from database.session import SessionLocal
        from database.models import ScanResult, Stock
    except Exception as e:
        log.warning(f"DB import failed ({e}) — skipping Stage 2 export")
        return

    db = SessionLocal()
    try:
        for tf in ["daily", "weekly", "monthly"]:
            results = (
                db.query(ScanResult)
                .filter(ScanResult.stage == "Stage 2", ScanResult.timeframe == tf)
                .order_by(ScanResult.composite_score.desc())
                .limit(500)
                .all()
            )
            output = []
            for r in results:
                stock = db.query(Stock).filter(Stock.symbol == r.symbol).first()
                output.append({
                    "symbol":      r.symbol,
                    "name":        stock.name    if stock else r.symbol,
                    "sector":      stock.sector  if stock else "Unknown",
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

            payload = {"timeframe": tf, "count": len(output), "data": output}
            _write_json(os.path.join(API_EXPORT_DIR, f"stage2_{tf}.json"), payload)
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# Export: /api/market  (full universe from latest_full_scan.csv)
# ─────────────────────────────────────────────────────────────────────────────

def export_market():
    csv_path  = os.path.join(SCAN_RESULTS_DIR, "latest_full_scan.csv")
    fund_path = os.path.join(SCAN_RESULTS_DIR, "fundamentals.json")

    if not os.path.exists(csv_path):
        log.warning("latest_full_scan.csv not found — skipping market export")
        _write_json(os.path.join(API_EXPORT_DIR, "market.json"), {"total": 0, "count": 0, "data": []})
        return

    # Build fundamentals lookup
    fund_lookup = {}
    fund_data = _load_json(fund_path, default={})
    for s in fund_data.get("stocks", []):
        sym  = s.get("s", "")
        base = sym.replace(".NS", "").replace(".BO", "")
        fund_lookup[sym]  = s
        fund_lookup[base] = s

    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get("ticker", "")
            base   = ticker.replace(".NS", "").replace(".BO", "")
            fund   = fund_lookup.get(ticker) or fund_lookup.get(base) or {}

            def _f(k):
                try:    return float(row.get(k) or 0)
                except: return 0.0

            rows.append({
                "ticker":    ticker,
                "symbol":    base,
                "name":      fund.get("name", base),
                "sector":    fund.get("sector", ""),
                "mcap_code": fund.get("mcap_code", ""),
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

    rows.sort(key=lambda r: r.get("ret_1m") or 0, reverse=True)
    payload = {"total": len(rows), "count": len(rows), "data": rows}
    _write_json(os.path.join(API_EXPORT_DIR, "market.json"), payload)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("📤 Exporting static API JSON files...")
    try:
        log.info("  → summary")
        export_summary()

        log.info("  → top-performers (6 timeframes)")
        export_top_performers()

        log.info("  → stage2 candidates (daily / weekly / monthly)")
        export_stage2()

        log.info("  → full market scan")
        export_market()

        log.info(f"✅ Static API exported to {API_EXPORT_DIR}")
    except Exception as e:
        log.error(f"❌ Export failed: {e}")
        raise
