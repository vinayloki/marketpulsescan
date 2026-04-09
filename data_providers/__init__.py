"""
MarketPulse India — Data Providers Package
"""
from .base_provider import BaseDataProvider
from .nse_direct_provider import NSEDirectProvider
from .yfinance_provider import YFinanceProvider

__all__ = ["BaseDataProvider", "NSEDirectProvider", "YFinanceProvider"]


def get_provider() -> BaseDataProvider:
    """
    Factory: returns NSEDirectProvider with YFinanceProvider as fallback.
    The caller never needs to know which one is active.
    """
    return NSEDirectProvider(fallback=YFinanceProvider())
