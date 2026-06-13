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
@router.delete("/{watchlist_id}")
def delete_watchlist(watchlist_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Watchlist deleted"}

@router.put("/{watchlist_id}")
def update_watchlist(watchlist_id: int, item: WatchlistCreate, db: Session = Depends(get_db)):
    db_item = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    db_item.name = item.name
    db_item.symbols = item.symbols
    db.commit()
    db.refresh(db_item)
    return db_item
