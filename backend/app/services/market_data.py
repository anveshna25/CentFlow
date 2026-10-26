from collections.abc import Sequence
from datetime import datetime
from typing import Any, Optional

from app.core.config import get_settings
from app.domain.models import Instrument, Price
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)
from app.providers.cache import CachedMarketDataProvider
from app.providers.registry import get_provider


from app.services.history import HistoricalSeries, HistoryService
from app.services.quote import MarketQuote, QuoteService


class MarketDataService:
    """Application service for orchestrating market data operations.

    Serves as the clean architectural boundary between API/business layers
    and external market data provider adapters, incorporating caching
    and rate-limiting layers.
    """

    def __init__(
        self,
        provider: Optional[BaseMarketDataProvider] = None,
        enable_cache: Optional[bool] = None,
    ) -> None:
        raw_provider = provider or get_provider()
        settings = get_settings()
        should_cache = enable_cache if enable_cache is not None else settings.market_data_cache_enabled

        if should_cache and not isinstance(raw_provider, CachedMarketDataProvider):
            self._provider = CachedMarketDataProvider(
                provider=raw_provider,
                quote_ttl=settings.quote_cache_ttl_seconds,
                history_ttl=settings.history_cache_ttl_seconds,
                search_ttl=settings.search_cache_ttl_seconds,
                enabled=True,
            )
        else:
            self._provider = raw_provider

        self._quote_service = QuoteService(provider=self._provider, enable_cache=False)
        self._history_service = HistoryService(provider=self._provider)

    @property
    def provider(self) -> BaseMarketDataProvider:
        """The active market data provider instance."""
        return self._provider

    @property
    def quote_service(self) -> QuoteService:
        """The dedicated QuoteService instance."""
        return self._quote_service

    @property
    def history_service(self) -> HistoryService:
        """The dedicated HistoryService instance."""
        return self._history_service

    @property
    def capabilities(self):
        """Operational capabilities declared by active market data provider."""
        return self._provider.capabilities

    async def close(self) -> None:
        """Close provider resources."""
        await self._provider.close()

    def get_cache_stats(self) -> Optional[dict[str, Any]]:
        """Retrieve cache performance statistics if caching layer is active."""
        if isinstance(self._provider, CachedMarketDataProvider):
            return self._provider.get_stats()
        return None

    async def clear_cache(self) -> None:
        """Clear cache if caching layer is active."""
        if isinstance(self._provider, CachedMarketDataProvider):
            await self._provider.clear_cache()

    async def get_quote(self, symbol: str) -> MarketQuote:
        """Fetch normalized, validated quote for an instrument symbol."""
        return await self._quote_service.get_quote(symbol)

    async def get_quotes(
        self,
        symbols: Sequence[str],
        allow_partial: bool = True,
    ) -> list[MarketQuote]:
        """Fetch batch of normalized, validated quotes for multiple instrument symbols."""
        return await self._quote_service.get_quotes(symbols, allow_partial=allow_partial)

    async def get_historical_bars(
        self,
        symbol: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: str = "1d",
        range: Optional[str] = None,
        days: Optional[int] = None,
    ) -> Sequence[ProviderBar]:
        """Fetch historical price bars for an instrument symbol."""
        series = await self._history_service.get_historical_series(
            symbol=symbol,
            range_str=range,
            days=days,
            start=start,
            end=end,
            interval=interval,
        )
        return series.bars

    async def get_historical_series(
        self,
        symbol: str,
        range_str: Optional[str] = None,
        days: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        interval: Optional[str] = None,
    ) -> HistoricalSeries:
        """Fetch full historical series with validation and summary metrics."""
        return await self._history_service.get_historical_series(
            symbol=symbol,
            range_str=range_str,
            days=days,
            start=start,
            end=end,
            interval=interval,
        )

    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]:
        """Search available instruments matching a symbol or name query."""
        if not query or not query.strip():
            return []
        return await self._provider.search_instruments(query.strip())

    async def lookup_asset(self, symbol: str) -> Optional[ProviderInstrument]:
        """Fetch canonical instrument record for a specific symbol directly from provider."""
        if not symbol or not symbol.strip():
            return None
        return await self._provider.lookup_asset(symbol.strip().upper())

    async def get_provider_status(self) -> ProviderStatus:
        """Check provider connectivity and operational status."""
        return await self._provider.get_status()

    @staticmethod
    def to_domain_price(quote: ProviderQuote, instrument: Instrument) -> Price:
        """Convert a normalized ProviderQuote into a core CentFlow domain Price model."""
        return Price(
            instrument=instrument,
            value=quote.price,
            currency=quote.currency,
            timestamp=quote.timestamp,
        )
