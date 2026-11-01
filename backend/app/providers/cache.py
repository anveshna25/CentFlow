from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime
import logging
import time
from typing import Any, Callable, Optional

from app.core.cache import AsyncMemoryCache
from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from app.core.errors import NotFoundError, ValidationError, sanitize_provider_error
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderCapabilities,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class CachedMarketDataProvider(BaseMarketDataProvider):
    """Proxy decorator around any BaseMarketDataProvider providing multi-tier
    in-memory and persistence TTL caching, single-flight request coalescing,
    circuit breaking, graceful provider failover, and stale-while-revalidate degradation.
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
        circuit_breaker: Optional[CircuitBreaker] = None,
        fallback_provider: Optional[BaseMarketDataProvider] = None,
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
        self._circuit_breaker = circuit_breaker
        self._fallback_provider = fallback_provider

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
    def fallback_provider(self) -> Optional[BaseMarketDataProvider]:
        """Reference to optional failover backup provider."""
        return self._fallback_provider

    @property
    def circuit_breaker(self) -> Optional[CircuitBreaker]:
        """Reference to the active circuit breaker protecting this provider."""
        return self._circuit_breaker

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
        if self._circuit_breaker:
            stats["circuit_breaker"] = self._circuit_breaker.get_metrics()
        return stats

    async def clear_cache(self, prefix: Optional[str] = None) -> int:
        """Flush cached entries matching prefix, or all entries if prefix is None."""
        return await self._cache.clear(prefix=prefix)

    async def purge_expired(self) -> int:
        """Manually purge expired or dead cache entries."""
        return await self._cache.purge_expired()

    def _get_stale_cached_quote(self, cache_key: str) -> Optional[ProviderQuote]:
        """Attempt to extract cached quote entry even if past primary TTL."""
        entry = self._cache._store.get(cache_key)
        if entry is not None and entry.value is not None:
            now = time.monotonic()
            if not entry.is_dead(now) or (now - entry.created_at) <= self._stale_grace_ttl:
                quote = entry.value
                return replace(quote, is_stale=True)
        return None

    async def _try_quote_failover(self, clean_symbol: str, cache_key: str) -> Optional[ProviderQuote]:
        """Attempt graceful multi-tier failover: stale cache -> db persistence -> fallback provider."""
        # 1. Check in-memory stale cache
        stale_cached = self._get_stale_cached_quote(cache_key)
        if stale_cached is not None:
            logger.info("Serving stale in-memory cached quote for '%s' during failover", clean_symbol)
            return stale_cached

        # 2. Check persistence DB fallback
        if self._db_fallback_fn is not None:
            try:
                persisted = self._db_fallback_fn(clean_symbol)
                if persisted is not None:
                    logger.info("Serving persisted price for '%s' during failover", clean_symbol)
                    return replace(persisted, is_stale=True) if hasattr(persisted, "is_stale") else persisted
            except Exception as e:
                logger.debug("Database fallback lookup failed for '%s': %s", clean_symbol, e)

        # 3. Check fallback provider
        if self._fallback_provider is not None:
            try:
                logger.info("Routing '%s' quote to fallback provider '%s'", clean_symbol, self._fallback_provider.name)
                fb_quote = await self._fallback_provider.get_quote(clean_symbol)
                if fb_quote is not None:
                    return replace(
                        fb_quote,
                        is_stale=True,
                    )
            except Exception as e:
                logger.warning("Fallback provider '%s' failed for '%s': %s", self._fallback_provider.name, clean_symbol, e)

        return None

    async def get_quote(self, symbol: str) -> ProviderQuote:
        """Fetch quote with short-lived TTL caching, single-flight coalescing,
        circuit breaker protection, and multi-tier failover.
        """
        clean_symbol = symbol.strip().upper()
        cache_key = f"quote:{clean_symbol}"

        # Check circuit breaker before attempting upstream call
        if self._circuit_breaker and not self._circuit_breaker.can_execute():
            failover_quote = await self._try_quote_failover(clean_symbol, cache_key)
            if failover_quote is not None:
                return failover_quote
            raise CircuitBreakerOpenError(
                provider_name=self.name,
                reset_timeout_seconds=self._circuit_breaker.get_remaining_cooldown(),
            )

        if not self._enabled:
            try:
                quote = await self._provider.get_quote(clean_symbol)
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return quote
            except Exception as exc:
                if isinstance(exc, (NotFoundError, ValidationError)):
                    raise
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure(exc)
                failover = await self._try_quote_failover(clean_symbol, cache_key)
                if failover is not None:
                    return failover
                raise sanitize_provider_error(exc, self.name)

        async def _fetch_from_provider() -> ProviderQuote:
            try:
                res = await self._provider.get_quote(clean_symbol)
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return res
            except Exception as exc:
                if not isinstance(exc, (NotFoundError, ValidationError)):
                    if self._circuit_breaker:
                        self._circuit_breaker.record_failure(exc)
                raise

        try:
            quote = await self._cache.get_or_set(
                key=cache_key,
                factory=_fetch_from_provider,
                ttl_seconds=self._quote_ttl,
                stale_ttl_seconds=self._stale_grace_ttl,
                fallback_on_error=True,
            )
            # If entry in cache was expired when served (stale-while-revalidate), mark as stale
            now = time.monotonic()
            entry = self._cache._store.get(cache_key)
            if entry is not None and entry.is_expired(now):
                return replace(quote, is_stale=True)
            return quote
        except Exception as exc:
            if isinstance(exc, (NotFoundError, ValidationError)):
                raise
            # Multi-tier failover on cache miss + provider error
            failover = await self._try_quote_failover(clean_symbol, cache_key)
            if failover is not None:
                return failover
            raise sanitize_provider_error(exc, self.name)

    async def _try_history_failover(
        self,
        clean_symbol: str,
        start: datetime,
        end: datetime,
        clean_interval: str,
    ) -> Optional[Sequence[ProviderBar]]:
        """Attempt graceful failover for historical bars."""
        # 1. Persistence fallback
        if self._db_history_fallback_fn is not None:
            try:
                persisted = self._db_history_fallback_fn(clean_symbol, start, end, clean_interval)
                if persisted:
                    logger.info("Serving %d persisted bars for '%s' during failover", len(persisted), clean_symbol)
                    return persisted
            except Exception as e:
                logger.debug("Database history fallback failed for '%s': %s", clean_symbol, e)

        # 2. Fallback provider
        if self._fallback_provider is not None:
            try:
                logger.info("Routing '%s' history to fallback provider '%s'", clean_symbol, self._fallback_provider.name)
                return await self._fallback_provider.get_historical_bars(
                    symbol=clean_symbol,
                    start=start,
                    end=end,
                    interval=clean_interval,
                )
            except Exception as e:
                logger.warning("Fallback provider '%s' history failed for '%s': %s", self._fallback_provider.name, clean_symbol, e)

        return None

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> Sequence[ProviderBar]:
        """Fetch historical bars with medium-lived TTL caching, request coalescing,
        circuit breaker protection, and persistence failover.
        """
        clean_symbol = symbol.strip().upper()
        clean_interval = interval.strip().lower()
        p1 = int(start.timestamp())
        p2 = int(end.timestamp())
        cache_key = f"history:{clean_symbol}:{p1}:{p2}:{clean_interval}"

        # Check circuit breaker before attempting upstream call
        if self._circuit_breaker and not self._circuit_breaker.can_execute():
            failover_bars = await self._try_history_failover(clean_symbol, start, end, clean_interval)
            if failover_bars is not None:
                return failover_bars
            raise CircuitBreakerOpenError(
                provider_name=self.name,
                reset_timeout_seconds=self._circuit_breaker.get_remaining_cooldown(),
            )

        if not self._enabled:
            try:
                bars = await self._provider.get_historical_bars(
                    symbol=clean_symbol,
                    start=start,
                    end=end,
                    interval=clean_interval,
                )
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return bars
            except Exception as exc:
                if isinstance(exc, (NotFoundError, ValidationError)):
                    raise
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure(exc)
                failover = await self._try_history_failover(clean_symbol, start, end, clean_interval)
                if failover is not None:
                    return failover
                raise sanitize_provider_error(exc, self.name)

        async def _fetch_from_provider() -> Sequence[ProviderBar]:
            try:
                res = await self._provider.get_historical_bars(
                    symbol=clean_symbol,
                    start=start,
                    end=end,
                    interval=clean_interval,
                )
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return res
            except Exception as exc:
                if not isinstance(exc, (NotFoundError, ValidationError)):
                    if self._circuit_breaker:
                        self._circuit_breaker.record_failure(exc)
                raise

        try:
            return await self._cache.get_or_set(
                key=cache_key,
                factory=_fetch_from_provider,
                ttl_seconds=self._history_ttl,
                stale_ttl_seconds=self._stale_grace_ttl,
                fallback_on_error=True,
            )
        except Exception as exc:
            if isinstance(exc, (NotFoundError, ValidationError)):
                raise
            failover = await self._try_history_failover(clean_symbol, start, end, clean_interval)
            if failover is not None:
                return failover
            raise sanitize_provider_error(exc, self.name)

    async def search_instruments(
        self,
        query: str = "",
        asset_type: Optional[str] = None,
    ) -> Sequence[ProviderInstrument]:
        """Fetch instrument search results with long-lived TTL caching and failover."""
        clean_query = (query or "").strip().lower()
        clean_type = (asset_type or "").strip().lower()
        if clean_type == "all":
            clean_type = ""

        if not clean_query and not clean_type:
            return []

        async def _call_provider() -> Sequence[ProviderInstrument]:
            try:
                res = await self._provider.search_instruments(clean_query, asset_type=asset_type)
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return res
            except TypeError:
                res = await self._provider.search_instruments(clean_query)
                if self._circuit_breaker:
                    self._circuit_breaker.record_success()
                return res
            except Exception as exc:
                if self._circuit_breaker:
                    self._circuit_breaker.record_failure(exc)
                if self._fallback_provider is not None:
                    try:
                        return await self._fallback_provider.search_instruments(clean_query, asset_type=asset_type)
                    except Exception:
                        pass
                raise sanitize_provider_error(exc, self.name)

        if not self._enabled:
            return await _call_provider()

        cache_key = f"search:{clean_query}:{clean_type}"
        return await self._cache.get_or_set(
            key=cache_key,
            factory=_call_provider,
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
        """Check status of underlying provider and attach circuit breaker diagnostics."""
        base_status = await self._provider.get_status()
        if self._circuit_breaker:
            cb_metrics = self._circuit_breaker.get_metrics()
            # If circuit breaker is OPEN, reflect in active status
            is_active = base_status.is_active and (self._circuit_breaker.can_execute())
            message = base_status.message
            if not self._circuit_breaker.can_execute():
                message = f"Circuit breaker OPEN ({int(self._circuit_breaker.get_remaining_cooldown())}s cooldown remaining)"
            return replace(
                base_status,
                is_active=is_active,
                message=message,
                circuit_breaker=cb_metrics,
            )
        return base_status

    async def close(self) -> None:
        """Close underlying and fallback provider resources."""
        await self._provider.close()
        if self._fallback_provider:
            await self._fallback_provider.close()
