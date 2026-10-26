from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
import time
from typing import Any, Callable, Optional

from app.core.cache import AsyncMemoryCache
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderCapabilities,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)


class CachedMarketDataProvider(BaseMarketDataProvider):
    """Proxy decorator around any BaseMarketDataProvider providing multi-tier
    in-memory and persistence TTL caching, single-flight request coalescing,
    pluggable eviction policies, and stale-while-revalidate graceful degradation.
    """

    def __init__(
        self,
        provider: BaseMarketDataProvider,
        quote_ttl: float = 15.0,
        history_ttl: float = 300.0,
        search_ttl: float = 600.0,
        asset_ttl: float = 1800.0,
        stale_grace_ttl: float = 86400.0,
        cache: Optional[AsyncMemoryCache] = None,
        max_capacity: int = 1000,
        eviction_policy: str = "lru",
        enabled: bool = True,
        db_fallback_fn: Optional[Callable[[str], Optional[ProviderQuote]]] = None,
        db_history_fallback_fn: Optional[Callable[[str, datetime, datetime, str], Sequence[ProviderBar]]] = None,
    ) -> None:
        self._provider = provider
        self._quote_ttl = quote_ttl
        self._history_ttl = history_ttl
        self._search_ttl = search_ttl
        self._asset_ttl = asset_ttl
        self._stale_grace_ttl = stale_grace_ttl
        self._enabled = enabled
        self._db_fallback_fn = db_fallback_fn
        self._db_history_fallback_fn = db_history_fallback_fn

        if cache is not None:
            self._cache = cache
        else:
            self._cache = AsyncMemoryCache(
                max_capacity=max_capacity,
                eviction_policy=eviction_policy,
            )

    @property
    def name(self) -> str:
        """Name of the wrapped underlying provider."""
        return self._provider.name

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Operational capabilities inherited from underlying provider."""
        return self._provider.capabilities

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
        """Retrieve cache hit/miss/coalescing and telemetry performance metrics."""
        stats = self._cache.get_stats()
        stats.update(
            {
                "enabled": self._enabled,
                "ttl_config": {
                    "quote_ttl": self._quote_ttl,
                    "history_ttl": self._history_ttl,
                    "search_ttl": self._search_ttl,
                    "asset_ttl": self._asset_ttl,
                    "stale_grace_ttl": self._stale_grace_ttl,
                },
            }
        )
        return stats

    async def clear_cache(self, prefix: Optional[str] = None) -> int:
        """Flush cached entries matching prefix, or all entries if prefix is None.

        Returns:
            Count of removed entries.
        """
        return await self._cache.clear(prefix=prefix)

    async def purge_expired(self) -> int:
        """Manually purge expired or dead cache entries.

        Returns:
            Count of removed entries.
        """
        return await self._cache.purge_expired()

    async def get_quote(self, symbol: str) -> ProviderQuote:
        """Fetch quote with short-lived TTL caching, single-flight coalescing,
        and stale-while-revalidate fallback during provider outages.
        """
        clean_symbol = symbol.strip().upper()
        if not self._enabled:
            return await self._provider.get_quote(clean_symbol)

        cache_key = f"quote:{clean_symbol}"

        try:
            quote = await self._cache.get_or_set(
                key=cache_key,
                factory=lambda: self._provider.get_quote(clean_symbol),
                ttl_seconds=self._quote_ttl,
                stale_ttl_seconds=self._stale_grace_ttl,
                fallback_on_error=True,
            )
            # If entry in cache was expired when served (fallback), mark quote as stale
            now = time.monotonic()
            entry = self._cache._store.get(cache_key)
            if entry is not None and entry.is_expired(now):
                return replace(quote, is_stale=True)
            return quote
        except Exception:
            # Tier-2 persistence fallback: check database for last price observation
            if self._db_fallback_fn is not None:
                try:
                    persisted = self._db_fallback_fn(clean_symbol)
                    if persisted is not None:
                        return replace(persisted, is_stale=True) if hasattr(persisted, "is_stale") else persisted
                except Exception:
                    pass
            raise

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        """Fetch historical bars with medium-lived TTL caching, request coalescing,
        and persistence fallback.
        """
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

        try:
            return await self._cache.get_or_set(
                key=cache_key,
                factory=lambda: self._provider.get_historical_bars(
                    symbol=clean_symbol,
                    start=start,
                    end=end,
                    interval=clean_interval,
                ),
                ttl_seconds=self._history_ttl,
                stale_ttl_seconds=self._stale_grace_ttl,
                fallback_on_error=True,
            )
        except Exception:
            # Tier-2 persistence fallback
            if self._db_history_fallback_fn is not None:
                try:
                    persisted = self._db_history_fallback_fn(clean_symbol, start, end, clean_interval)
                    if persisted:
                        return persisted
                except Exception:
                    pass
            raise

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
            stale_ttl_seconds=self._stale_grace_ttl,
            fallback_on_error=True,
        )

    async def lookup_asset(self, symbol: str) -> Optional[ProviderInstrument]:
        """Fetch asset lookup record with long-lived metadata TTL caching."""
        clean_symbol = symbol.strip().upper()
        if not clean_symbol:
            return None
        if not self._enabled:
            return await self._provider.lookup_asset(clean_symbol)

        cache_key = f"lookup:{clean_symbol}"
        return await self._cache.get_or_set(
            key=cache_key,
            factory=lambda: self._provider.lookup_asset(clean_symbol),
            ttl_seconds=self._asset_ttl,
            stale_ttl_seconds=self._stale_grace_ttl,
            fallback_on_error=True,
        )

    async def get_status(self) -> ProviderStatus:
        """Check status of underlying provider without caching (live bypass)."""
        return await self._provider.get_status()

    async def close(self) -> None:
        """Close underlying provider resources."""
        await self._provider.close()
