from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class ProviderQuote:
    """Normalized real-time or delayed quote from a market data provider."""

    symbol: str
    price: Decimal
    currency: str
    timestamp: datetime
    volume: Optional[Decimal] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None


@dataclass(frozen=True)
class ProviderBar:
    """Normalized OHLCV time-series bar from a market data provider."""

    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class ProviderInstrument:
    """Normalized instrument search or metadata record from a market data provider."""

    symbol: str
    name: str
    asset_type: str
    currency: Optional[str] = None
    exchange: Optional[str] = None
    market: Optional[str] = None


@dataclass(frozen=True)
class ProviderStatus:
    """Status and health report for a market data provider."""

    name: str
    is_active: bool
    message: Optional[str] = None


class BaseMarketDataProvider(ABC):
    """Abstract interface that all CentFlow market data providers must implement.
    
    This contract decouples the platform from any single external market data vendor
    (e.g., Mock, Yahoo Finance, Alpha Vantage, Polygon, Financial Modeling Prep).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier of the provider (e.g. 'mock', 'yahoo', 'polygon')."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> ProviderQuote:
        """Fetch the latest normalized quote for the specified instrument symbol."""
        pass

    @abstractmethod
    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        """Fetch historical OHLCV bars for the specified instrument and date range."""
        pass

    @abstractmethod
    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]:
        """Search instruments matching the query string by symbol or name."""
        pass

    @abstractmethod
    async def get_status(self) -> ProviderStatus:
        """Check provider connectivity and health status."""
        pass
