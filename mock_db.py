import logging
from datetime import datetime
from database.session import SessionLocal
from database.models import Stock, ScanResult

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("marketpulse.mock")

def insert_mock_data():
    log.info("Inserting mock data into SQLite due to yfinance rate limits...")
    db = SessionLocal()
    
    mocks = [
        {"symbol": "TATASTEEL.NS", "name": "Tata Steel", "sector": "Metals", "score": 92, "rs_score": 88, "price": 154.2, "sma_50": 140, "sma_200": 125},
        {"symbol": "RELIANCE.NS", "name": "Reliance Ind", "sector": "Energy", "score": 85, "rs_score": 81, "price": 2950, "sma_50": 2800, "sma_200": 2650},
        {"symbol": "ZOMATO.NS", "name": "Zomato Ltd", "sector": "Consumer Services", "score": 95, "rs_score": 94, "price": 165, "sma_50": 145, "sma_200": 110},
        {"symbol": "BSE.BO", "name": "BSE Limited", "sector": "Financials", "score": 98, "rs_score": 96, "price": 2800, "sma_50": 2400, "sma_200": 2100},
        {"symbol": "TATAMOTORS.NS", "name": "Tata Motors", "sector": "Automobile", "score": 88, "rs_score": 85, "price": 980, "sma_50": 920, "sma_200": 850}
    ]
    
    for m in mocks:
        # Check stock
        stock = db.query(Stock).filter(Stock.symbol == m["symbol"]).first()
        if not stock:
            stock = Stock(symbol=m["symbol"], name=m["name"], sector=m["sector"])
            db.add(stock)
            
        # Check result
        result = db.query(ScanResult).filter(ScanResult.symbol == m["symbol"]).first()
        if not result:
            result = ScanResult(symbol=m["symbol"])
            db.add(result)
            
        result.stage = "Stage 2"
        result.composite_score = m["score"]
        result.rs_score = m["rs_score"]
        result.d_close = m["price"]
        result.d_ema50 = m["sma_50"]
        result.d_ema200 = m["sma_200"]
        result.price_above_50 = True
        result.price_above_200 = True
        result.ema50_above_200 = True
        result.updated_at = datetime.utcnow()
        
    db.commit()
    db.close()
    log.info("Mock data successfully inserted into the database.")

if __name__ == "__main__":
    insert_mock_data()
