from sqlalchemy.orm import Session
from datetime import datetime
import logging

from database.models import Stock, ScanResult
from database.session import SessionLocal

log = logging.getLogger("marketpulse.db_updater")

def update_stage2_results(scanner_results: dict):
    """
    Takes the output of Stage2Scanner (dict of ticker -> ScanResult model)
    and persists it into the SQLite database.
    """
    db: Session = SessionLocal()
    try:
        log.info("Persisting Stage 2 scan results to database...")
        
        # We might want to clear old results, or just upsert
        # For simplicity, we'll upsert (update if exists, otherwise insert)
        
        for ticker, result in scanner_results.items():
            # Ensure stock exists in DB
            stock = db.query(Stock).filter(Stock.symbol == ticker).first()
            if not stock:
                # Create a placeholder stock if fundamentals haven't run yet
                stock = Stock(symbol=ticker, name=ticker)
                db.add(stock)
                db.commit()
                db.refresh(stock)
            
            # Upsert ScanResult
            db_result = db.query(ScanResult).filter(ScanResult.symbol == ticker).first()
            if not db_result:
                db_result = ScanResult(symbol=ticker)
                db.add(db_result)
            
            db_result.updated_at = datetime.utcnow()
            db_result.stage = "Stage 2" # Since the scanner only returns stocks meeting Stage 2
            db_result.composite_score = result.score
            
            # Extract indicators
            inds = result.indicators
            db_result.rs_score = inds.get("rs_rating")
            db_result.d_close = inds.get("price")
            db_result.d_ema50 = inds.get("sma_50")
            db_result.d_ema200 = inds.get("sma_200")
            
            # Basic daily conditions
            if db_result.d_close and db_result.d_ema50:
                db_result.price_above_50 = db_result.d_close > db_result.d_ema50
            if db_result.d_close and db_result.d_ema200:
                db_result.price_above_200 = db_result.d_close > db_result.d_ema200
            if db_result.d_ema50 and db_result.d_ema200:
                db_result.ema50_above_200 = db_result.d_ema50 > db_result.d_ema200
            
        db.commit()
        log.info(f"Successfully persisted {len(scanner_results)} Stage 2 records.")
    except Exception as e:
        log.error(f"Error persisting to database: {e}")
        db.rollback()
    finally:
        db.close()
