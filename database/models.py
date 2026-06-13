from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .session import Base

class Stock(Base):
    __tablename__ = "stocks"

    symbol = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    sector = Column(String, index=True)
    industry = Column(String, index=True)
    mcap_category = Column(String)  # 'L', 'M', 'S'
    mcap_cr = Column(Float)
    exchange = Column(String) # 'NSE' or 'BSE'
    
    # Fundamental basic fields
    pe = Column(Float)
    eps = Column(Float)
    dy = Column(Float) # Dividend Yield
    
    # Relationships
    candles = relationship("Candle", back_populates="stock", cascade="all, delete-orphan")
    scan_results = relationship("ScanResult", back_populates="stock", cascade="all, delete-orphan")

class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("stocks.symbol"), index=True)
    date = Column(Date, index=True)
    timeframe = Column(String, index=True) # '1d', '1wk', '1mo'
    
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)

    stock = relationship("Stock", back_populates="candles")

class ScanResult(Base):
    """Stores the latest stage 2 scan results for a stock"""
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, ForeignKey("stocks.symbol"), index=True, unique=True)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    stage = Column(String) # 'Stage 1', 'Stage 2', 'Stage 3', 'Stage 4'
    rs_score = Column(Float) # Relative Strength Score (0-100)
    trend_score = Column(Float)
    composite_score = Column(Float)
    
    # Weekly indicators
    wk_close = Column(Float)
    wk_ma30_val = Column(Float)
    wk_ma30_trend = Column(String) # 'Rising', 'Falling', 'Flat'
    
    # Daily indicators
    d_close = Column(Float)
    d_ema50 = Column(Float)
    d_ema200 = Column(Float)
    
    # Daily conditions
    price_above_50 = Column(Boolean)
    price_above_200 = Column(Boolean)
    ema50_above_200 = Column(Boolean)
    
    stock = relationship("Stock", back_populates="scan_results")

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    symbols = Column(String) # Comma-separated list of symbols
    created_at = Column(DateTime, default=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    condition = Column(String) # e.g. "ENTERS_STAGE_2", "PRICE_ABOVE_30W_MA"
    target_value = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
