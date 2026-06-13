from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from database.session import get_db
from database.models import Watchlist

router = APIRouter()

class WatchlistCreate(BaseModel):
    name: str
    symbols: str

@router.get("/")
def get_watchlists(db: Session = Depends(get_db)):
    return db.query(Watchlist).all()

@router.post("/")
def create_watchlist(item: WatchlistCreate, db: Session = Depends(get_db)):
    existing = db.query(Watchlist).filter(Watchlist.name == item.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Watchlist already exists")
    db_item = Watchlist(name=item.name, symbols=item.symbols)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
