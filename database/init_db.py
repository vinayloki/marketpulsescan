from database.session import engine, Base
from database.models import Stock, Candle, ScanResult, Watchlist, Alert

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")

if __name__ == "__main__":
    init_db()
