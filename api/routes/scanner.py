from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database.session import get_db
from database.models import ScanResult, Stock

router = APIRouter()

@router.get("/stage2")
def get_stage2_candidates(db: Session = Depends(get_db)):
    """Retrieve all stocks that currently meet Stage 2 criteria, ordered by composite score."""
    results = db.query(ScanResult).filter(ScanResult.stage == "Stage 2").order_by(ScanResult.composite_score.desc()).all()
    
    output = []
    for r in results:
        stock = db.query(Stock).filter(Stock.symbol == r.symbol).first()
        output.append({
            "symbol": r.symbol,
            "name": stock.name if stock else r.symbol,
            "sector": stock.sector if stock else "Unknown",
            "score": r.composite_score,
            "rs_rating": r.rs_score,
            "price": r.d_close,
            "sma_50": r.d_ema50,
            "sma_200": r.d_ema200
        })
    return {"count": len(output), "data": output}
