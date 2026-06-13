import logging
from database.session import SessionLocal
from database.models import Alert, ScanResult

log = logging.getLogger("marketpulse.alerts")

def process_alerts():
    """
    Evaluates active alerts against the latest ScanResults and triggers notifications.
    """
    db = SessionLocal()
    try:
        active_alerts = db.query(Alert).filter(Alert.is_active == True).all()
        
        for alert in active_alerts:
            result = db.query(ScanResult).filter(ScanResult.symbol == alert.symbol).first()
            if not result:
                continue
                
            triggered = False
            if alert.condition == "ENTERS_STAGE_2":
                triggered = (result.stage == "Stage 2")
            elif alert.condition == "RS_ABOVE_TARGET" and alert.target_value:
                triggered = (result.rs_score and result.rs_score >= alert.target_value)
            
            if triggered:
                log.info(f"🚨 ALERT TRIGGERED: {alert.symbol} ({alert.condition})")
                # Here we would dispatch an email, Telegram message, or Webhook.
                # For now, we'll just deactivate it after firing once.
                alert.is_active = False
                
        db.commit()
    except Exception as e:
        log.error(f"Error processing alerts: {e}")
    finally:
        db.close()
