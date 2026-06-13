import logging
import pandas as pd
from data_providers.yfinance_provider import YFinanceProvider
from scanners.stage2_scanner import Stage2Scanner
from database.db_updater import update_stage2_results

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("marketpulse.seeder")

def seed():
    log.info("Fetching a small universe (Nifty 50) for immediate UI testing...")
    tickers = [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "ITC", 
        "SBIN", "BHARTIARTL", "BAJFINANCE", "L&T", "KOTAKBANK", 
        "HINDUNILVR", "AXISBANK", "MARUTI", "SUNPHARMA", "ASIANPAINT",
        "TATASTEEL", "TITAN", "NTPC", "TATAMOTORS"
    ]
    yf_provider = YFinanceProvider()
    
    log.info(f"Downloading OHLCV for {len(tickers)} tickers...")
    ohlcv = yf_provider.fetch_ohlcv(tickers, period="2y", interval="1d")
    
    log.info("Running Stage 2 Scanner...")
    scanner = Stage2Scanner()
    results = scanner.scan(ohlcv)
    
    log.info(f"Found {len(results)} Stage 2 candidates out of the sample set.")
    
    log.info("Persisting to database...")
    update_stage2_results(results)
    
    log.info("Done! Refresh your frontend to see the seeded data.")

if __name__ == "__main__":
    seed()
