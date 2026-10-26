from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True)
class ProviderCapabilities:
    """Operational and functional capabilities declared by a market data provider."""

    supported_intervals: tuple[str, ...] = ("1d",)
    supports_search: bool = True
    supports_realtime: bool = True
    is_delayed: bool = False
    delay_minutes: int = 0


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
    latency_ms: Optional[float] = None
    capabilities: Optional[ProviderCapabilities] = None


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

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Operational capabilities declared by this market data provider."""
        return ProviderCapabilities()

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

    async def close(self) -> None:
        """Close any persistent network connections, HTTP sessions, or resources."""
        pass

    async def __aenter__(self) -> "BaseMarketDataProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit with resource release."""
        await self.close()
