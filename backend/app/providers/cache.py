from collections.abc import Sequence
from datetime import datetime
from typing import Any, Optional

from app.core.cache import AsyncMemoryCache
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)


class CachedMarketDataProvider(BaseMarketDataProvider):
    """Proxy decorator around any BaseMarketDataProvider providing in-memory
    TTL caching, request coalescing, and upstream rate-limit protection.
    """

    def __init__(
        self,
        provider: BaseMarketDataProvider,
        quote_ttl: float = 15.0,
        history_ttl: float = 300.0,
        search_ttl: float = 600.0,
        cache: Optional[AsyncMemoryCache] = None,
        enabled: bool = True,
    ) -> None:
        self._provider = provider
        self._quote_ttl = quote_ttl
        self._history_ttl = history_ttl
        self._search_ttl = search_ttl
        self._cache = cache if cache is not None else AsyncMemoryCache()
        self._enabled = enabled

    @property
    def name(self) -> str:
        """Name of the wrapped underlying provider."""
        return self._provider.name

    @property
    def underlying_provider(self) -> BaseMarketDataProvider:
        """Reference to the wrapped provider instance."""
        return self._provider

    @property
    def cache(self) -> AsyncMemoryCache:
        """Reference to the active memory cache."""
        return self._cache

    @property
    def is_cache_enabled(self) -> bool:
        """Whether caching layer is actively intercepting queries."""
        return self._enabled

    def get_stats(self) -> dict[str, Any]:
        """Retrieve cache hit/miss/coalescing performance metrics."""
        return self._cache.get_stats()

    async def clear_cache(self) -> None:
        """Flush all cached quotes, historical bars, and search records."""
        await self._cache.clear()

    async def get_quote(self, symbol: str) -> ProviderQuote:
        """Fetch quote with short-lived TTL caching and request coalescing."""
        clean_symbol = symbol.strip().upper()
        if not self._enabled:
            return await self._provider.get_quote(clean_symbol)

        cache_key = f"quote:{clean_symbol}"
        return await self._cache.get_or_set(
            key=cache_key,
            factory=lambda: self._provider.get_quote(clean_symbol),
            ttl_seconds=self._quote_ttl,
        )

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        """Fetch historical bars with medium-lived TTL caching."""
        clean_symbol = symbol.strip().upper()
        clean_interval = interval.strip().lower()
        if not self._enabled:
            return await self._provider.get_historical_bars(
                symbol=clean_symbol,
                start=start,
                end=end,
                interval=clean_interval,
            )

        p1 = int(start.timestamp())
        p2 = int(end.timestamp())
        cache_key = f"history:{clean_symbol}:{p1}:{p2}:{clean_interval}"

        return await self._cache.get_or_set(
            key=cache_key,
            factory=lambda: self._provider.get_historical_bars(
                symbol=clean_symbol,
                start=start,
                end=end,
                interval=clean_interval,
            ),
            ttl_seconds=self._history_ttl,
        )

    async def search_instruments(self, query: str) -> Sequence[ProviderInstrument]:
        """Fetch instrument search results with long-lived TTL caching."""
        clean_query = query.strip().lower()
        if not clean_query:
            return []
        if not self._enabled:
            return await self._provider.search_instruments(clean_query)

        cache_key = f"search:{clean_query}"
        return await self._cache.get_or_set(
            key=cache_key,
            factory=lambda: self._provider.search_instruments(clean_query),
            ttl_seconds=self._search_ttl,
        )

    async def get_status(self) -> ProviderStatus:
        """Check status of underlying provider without caching (live bypass)."""
        return await self._provider.get_status()
