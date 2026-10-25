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

    @property
    def provider(self) -> BaseMarketDataProvider:
        """The active market data provider instance."""
        return self._provider

    def get_cache_stats(self) -> Optional[dict[str, Any]]:
        """Retrieve cache performance statistics if caching layer is active."""
        if isinstance(self._provider, CachedMarketDataProvider):
            return self._provider.get_stats()
        return None

    async def clear_cache(self) -> None:
        """Clear cache if caching layer is active."""
        if isinstance(self._provider, CachedMarketDataProvider):
            await self._provider.clear_cache()

    async def get_quote(self, symbol: str) -> ProviderQuote:
        """Fetch normalized quote for an instrument symbol."""
        clean_symbol = symbol.strip().upper()
        return await self._provider.get_quote(clean_symbol)

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        """Fetch historical price bars for an instrument symbol."""
        clean_symbol = symbol.strip().upper()
        return await self._provider.get_historical_bars(
            symbol=clean_symbol,
            start=start,
            end=end,
            interval=interval,
        )

    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]:
        """Search available instruments matching a symbol or name query."""
        if not query or not query.strip():
            return []
        return await self._provider.search_instruments(query.strip())

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
