"""
MarketPulse India — Data Providers Package
"""
from .base_provider import BaseDataProvider
from .nse_direct_provider import NSEDirectProvider
from .yfinance_provider import YFinanceProvider
from .nse_archives_provider import NseArchivesProvider

__all__ = ["BaseDataProvider", "NSEDirectProvider", "YFinanceProvider", "NseArchivesProvider"]


def get_provider() -> BaseDataProvider:
    """
    Factory: returns NseArchivesProvider (for tickers/bhavcopy)
    with NSEDirectProvider (for NSE website fallbacks) 
    with YFinanceProvider as final fallback (and for full OHLCV history).
    """
    yf_provider = YFinanceProvider()
    direct_provider = NSEDirectProvider(fallback=yf_provider)
    return NseArchivesProvider(fallback=direct_provider)

