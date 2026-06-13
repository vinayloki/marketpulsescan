"""
mock_db.py — Seed the database with representative Stage 2 candidates
across Daily, Weekly, and Monthly timeframes for immediate UI testing.
"""
import logging
from datetime import datetime, UTC
from database.session import SessionLocal
from database.init_db import init_db
from database.models import Stock, ScanResult

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("marketpulse.mock")

STOCKS = [
    {"symbol": "TATASTEEL.NS",   "name": "Tata Steel Ltd",               "sector": "Metals & Mining",     "exchange": "NSE"},
    {"symbol": "RELIANCE.NS",    "name": "Reliance Industries Ltd",       "sector": "Energy",               "exchange": "NSE"},
    {"symbol": "ZOMATO.NS",      "name": "Zomato Ltd",                    "sector": "Consumer Services",    "exchange": "NSE"},
    {"symbol": "BSE.BO",         "name": "BSE Limited",                   "sector": "Financial Services",   "exchange": "BSE"},
    {"symbol": "TATAMOTORS.NS",  "name": "Tata Motors Ltd",               "sector": "Automobile",           "exchange": "NSE"},
    {"symbol": "HDFCBANK.NS",    "name": "HDFC Bank Ltd",                 "sector": "Banking",              "exchange": "NSE"},
    {"symbol": "ICICIBANK.NS",   "name": "ICICI Bank Ltd",                "sector": "Banking",              "exchange": "NSE"},
    {"symbol": "INFY.NS",        "name": "Infosys Ltd",                   "sector": "Information Technology","exchange": "NSE"},
    {"symbol": "TCS.NS",         "name": "Tata Consultancy Services",     "sector": "Information Technology","exchange": "NSE"},
    {"symbol": "SUNPHARMA.NS",   "name": "Sun Pharmaceutical Industries", "sector": "Pharmaceuticals",      "exchange": "NSE"},
    {"symbol": "TITAN.NS",       "name": "Titan Company Ltd",             "sector": "Consumer Goods",       "exchange": "NSE"},
    {"symbol": "ASIANPAINT.NS",  "name": "Asian Paints Ltd",              "sector": "Chemicals",            "exchange": "NSE"},
    {"symbol": "BHARTIARTL.NS",  "name": "Bharti Airtel Ltd",             "sector": "Telecom",              "exchange": "NSE"},
    {"symbol": "BAJFINANCE.NS",  "name": "Bajaj Finance Ltd",             "sector": "Financial Services",   "exchange": "NSE"},
    {"symbol": "MARUTI.NS",      "name": "Maruti Suzuki India Ltd",       "sector": "Automobile",           "exchange": "NSE"},
]

# Results per timeframe — mix of real-looking data
RESULTS = {
    "daily": [
        {"symbol": "TATASTEEL.NS",  "score": 92, "rs": 88,  "price": 154.2,  "f": 140.5,  "m": 130.2, "s": 125.1, "h52": 185.0, "l52": 108.0},
        {"symbol": "RELIANCE.NS",   "score": 85, "rs": 81,  "price": 2950.0, "f": 2800.0, "m": 2650.0,"s": 2600.0,"h52": 3180.0,"l52": 2210.0},
        {"symbol": "ZOMATO.NS",     "score": 95, "rs": 94,  "price": 265.0,  "f": 238.0,  "m": 205.0, "s": 188.0, "h52": 280.0, "l52": 140.0},
        {"symbol": "TATAMOTORS.NS", "score": 88, "rs": 85,  "price": 980.0,  "f": 920.0,  "m": 865.0, "s": 840.0, "h52": 1060.0,"l52": 720.0},
        {"symbol": "HDFCBANK.NS",   "score": 78, "rs": 75,  "price": 1720.0, "f": 1650.0, "m": 1580.0,"s": 1540.0,"h52": 1880.0,"l52": 1380.0},
        {"symbol": "INFY.NS",       "score": 82, "rs": 79,  "price": 1568.0, "f": 1480.0, "m": 1390.0,"s": 1350.0,"h52": 1690.0,"l52": 1180.0},
        {"symbol": "BHARTIARTL.NS", "score": 91, "rs": 89,  "price": 1845.0, "f": 1710.0, "m": 1580.0,"s": 1520.0,"h52": 1910.0,"l52": 1340.0},
        {"symbol": "BAJFINANCE.NS", "score": 83, "rs": 80,  "price": 8750.0, "f": 8300.0, "m": 7800.0,"s": 7550.0,"h52": 9240.0,"l52": 6500.0},
    ],
    "weekly": [
        {"symbol": "ZOMATO.NS",     "score": 97, "rs": 95,  "price": 265.0,  "f": 240.0,  "m": 210.0, "s": 190.0, "h52": 280.0, "l52": 140.0},
        {"symbol": "BHARTIARTL.NS", "score": 93, "rs": 91,  "price": 1845.0, "f": 1720.0, "m": 1590.0,"s": 1530.0,"h52": 1910.0,"l52": 1340.0},
        {"symbol": "TATASTEEL.NS",  "score": 88, "rs": 84,  "price": 154.2,  "f": 142.0,  "m": 132.0, "s": 126.0, "h52": 185.0, "l52": 108.0},
        {"symbol": "INFY.NS",       "score": 85, "rs": 82,  "price": 1568.0, "f": 1490.0, "m": 1400.0,"s": 1360.0,"h52": 1690.0,"l52": 1180.0},
        {"symbol": "TCS.NS",        "score": 80, "rs": 77,  "price": 4250.0, "f": 4050.0, "m": 3820.0,"s": 3680.0,"h52": 4600.0,"l52": 3200.0},
        {"symbol": "SUNPHARMA.NS",  "score": 87, "rs": 84,  "price": 1680.0, "f": 1580.0, "m": 1460.0,"s": 1400.0,"h52": 1750.0,"l52": 1200.0},
    ],
    "monthly": [
        {"symbol": "BHARTIARTL.NS", "score": 96, "rs": 93,  "price": 1845.0, "f": 1740.0, "m": 1610.0,"s": 1540.0,"h52": 1910.0,"l52": 1340.0},
        {"symbol": "ZOMATO.NS",     "score": 94, "rs": 92,  "price": 265.0,  "f": 245.0,  "m": 218.0, "s": 198.0, "h52": 280.0, "l52": 140.0},
        {"symbol": "TITAN.NS",      "score": 89, "rs": 86,  "price": 3650.0, "f": 3420.0, "m": 3180.0,"s": 3050.0,"h52": 3900.0,"l52": 2800.0},
        {"symbol": "ASIANPAINT.NS", "score": 78, "rs": 73,  "price": 2620.0, "f": 2500.0, "m": 2340.0,"s": 2250.0,"h52": 2900.0,"l52": 2100.0},
        {"symbol": "MARUTI.NS",     "score": 84, "rs": 81,  "price": 12800.0,"f": 12100.0,"m": 11300.0,"s": 10800.0,"h52": 13500.0,"l52": 9800.0},
    ],
}


def seed():
    log.info("Initialising database schema...")
    init_db()

    db = SessionLocal()
    try:
        # Upsert stocks
        for s in STOCKS:
            stock = db.query(Stock).filter(Stock.symbol == s["symbol"]).first()
            if not stock:
                stock = Stock(**s)
                db.add(stock)
            else:
                stock.name     = s["name"]
                stock.sector   = s["sector"]
                stock.exchange = s["exchange"]
        db.flush()

        # Upsert scan results per timeframe
        for timeframe, rows in RESULTS.items():
            for row in rows:
                rec = (
                    db.query(ScanResult)
                    .filter(ScanResult.symbol == row["symbol"], ScanResult.timeframe == timeframe)
                    .first()
                )
                if not rec:
                    rec = ScanResult(symbol=row["symbol"], timeframe=timeframe)
                    db.add(rec)

                rec.stage           = "Stage 2"
                rec.composite_score = row["score"]
                rec.rs_score        = row["rs"]
                rec.d_close         = row["price"]
                rec.d_ema50         = row["f"]
                rec.d_ema150        = row["m"]
                rec.d_ema200        = row["s"]
                rec.high_52w        = row["h52"]
                rec.low_52w         = row["l52"]

                p, f, m, s = row["price"], row["f"], row["m"], row["s"]
                rec.price_above_50   = p > f
                rec.price_above_150  = p > m
                rec.price_above_200  = p > s
                rec.ema50_above_150  = f > m
                rec.ema50_above_200  = f > s
                rec.ema150_above_200 = m > s
                rec.ema200_rising    = True
                rec.updated_at       = datetime.now(UTC)

        db.commit()
        log.info(f"✅ Seeded {sum(len(v) for v in RESULTS.values())} records across 3 timeframes.")
    except Exception as e:
        db.rollback()
        log.error(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
