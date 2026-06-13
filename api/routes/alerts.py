from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from database.session import get_db
from database.models import Alert

router = APIRouter()

class AlertCreate(BaseModel):
    symbol: str
    condition: str
    target_value: float = None

@router.get("/")
def get_alerts(db: Session = Depends(get_db)):
    return db.query(Alert).all()

@router.post("/")
def create_alert(item: AlertCreate, db: Session = Depends(get_db)):
    db_item = Alert(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
