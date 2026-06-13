import os
import json
import logging

logging.basicConfig(level=logging.INFO)

from api.routes.scanner import (
    get_dashboard_summary, 
    get_top_performers, 
    get_market_scan, 
    get_stage2_candidates
)
from database.session import SessionLocal

API_EXPORT_DIR = os.path.join(os.path.dirname(__file__), "scan_results", "api")
os.makedirs(API_EXPORT_DIR, exist_ok=True)

def export_all():
    db = SessionLocal()
    try:
        logging.info("Exporting /api/scanner/summary")
        with open(os.path.join(API_EXPORT_DIR, "summary.json"), "w") as f:
            json.dump(get_dashboard_summary(db=db), f)
            
        logging.info("Exporting /api/scanner/top-performers (all timeframes)")
        for tf in ["1W", "2W", "1M", "3M", "6M", "12M"]:
            with open(os.path.join(API_EXPORT_DIR, f"top-performers_{tf}.json"), "w") as f:
                json.dump(get_top_performers(timeframe=tf, limit=10), f)
                
        logging.info("Exporting /api/scanner/stage2 (daily, weekly, monthly)")
        for tf in ["daily", "weekly", "monthly"]:
            with open(os.path.join(API_EXPORT_DIR, f"stage2_{tf}.json"), "w") as f:
                json.dump(get_stage2_candidates(timeframe=tf, limit=500, db=db), f)
                
        logging.info("Exporting /api/scanner/market (full universe)")
        with open(os.path.join(API_EXPORT_DIR, "market.json"), "w") as f:
            json.dump(get_market_scan(sort_by="1M", order="desc", sector="", mcap="", limit=3500, offset=0), f)
            
        logging.info(f"✅ Static API exported successfully to {API_EXPORT_DIR}")
    except Exception as e:
        logging.error(f"Error exporting static API: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    export_all()
