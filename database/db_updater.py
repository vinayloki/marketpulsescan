import logging
from datetime import datetime, UTC
from sqlalchemy.exc import IntegrityError

from .session import SessionLocal
from .models import Stock, ScanResult

log = logging.getLogger("marketpulse.db_updater")


def update_stage2_results(scan_results: dict, timeframe: str = "daily"):
    """
    Persist Stage 2 scan results for a given timeframe to the database.

    Args:
        scan_results: dict mapping ticker -> ScanResult (engine.opportunity_model)
        timeframe: 'daily' | 'weekly' | 'monthly'
    """
    log.info(f"Persisting {len(scan_results)} Stage 2 results for timeframe='{timeframe}'...")

    db = SessionLocal()
    try:
        saved = 0
        for ticker, result in scan_results.items():
            ind = result.indicators or {}

            # Ensure stock row exists (bare minimum)
            stock = db.query(Stock).filter(Stock.symbol == ticker).first()
            if not stock:
                stock = Stock(symbol=ticker, name=ticker, exchange="NSE")
                db.add(stock)
                try:
                    db.flush()
                except IntegrityError:
                    db.rollback()
                    stock = db.query(Stock).filter(Stock.symbol == ticker).first()

            # Upsert ScanResult by (symbol, timeframe)
            record = (
                db.query(ScanResult)
                .filter(ScanResult.symbol == ticker, ScanResult.timeframe == timeframe)
                .first()
            )
            if not record:
                record = ScanResult(symbol=ticker, timeframe=timeframe)
                db.add(record)

            record.stage = "Stage 2"
            record.composite_score = result.score
            record.rs_score = ind.get("rs_rating", 0)
            record.d_close = ind.get("price")
            record.d_ema50 = ind.get("sma_50")
            record.d_ema150 = ind.get("sma_150")
            record.d_ema200 = ind.get("sma_200")
            record.high_52w = ind.get("high_52w")
            record.low_52w = ind.get("low_52w")

            # Condition flags
            price = ind.get("price") or 0
            sma50 = ind.get("sma_50") or 0
            sma150 = ind.get("sma_150") or 0
            sma200 = ind.get("sma_200") or 0

            record.price_above_50 = price > sma50
            record.price_above_150 = price > sma150
            record.price_above_200 = price > sma200
            record.ema50_above_150 = sma50 > sma150
            record.ema50_above_200 = sma50 > sma200
            record.ema150_above_200 = sma150 > sma200
            record.ema200_rising = ind.get("ema200_rising", False)

            record.updated_at = datetime.now(UTC)
            saved += 1

        db.commit()
        log.info(f"Successfully persisted {saved} Stage 2 records for timeframe='{timeframe}'.")
    except Exception as e:
        db.rollback()
        log.error(f"Error persisting Stage 2 results: {e}")
        raise
    finally:
        db.close()
