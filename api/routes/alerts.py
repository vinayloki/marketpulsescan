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
@router.delete("/{alert_id}")
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Alert).filter(Alert.id == alert_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(db_item)
    db.commit()
    return {"message": "Alert deleted"}

@router.put("/{alert_id}/toggle")
def toggle_alert(alert_id: int, db: Session = Depends(get_db)):
    db_item = db.query(Alert).filter(Alert.id == alert_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Alert not found")
    db_item.is_active = not db_item.is_active
    db.commit()
    db.refresh(db_item)
    return db_item
