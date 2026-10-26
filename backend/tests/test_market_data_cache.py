import asyncio
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

from app.core.cache import AsyncMemoryCache
from app.core.config import Settings
from app.providers.base import (
    BaseMarketDataProvider,
    ProviderBar,
    ProviderInstrument,
    ProviderQuote,
    ProviderStatus,
)
from app.providers.cache import CachedMarketDataProvider
from app.services.market_data import MarketDataService


class DummyProvider(BaseMarketDataProvider):
    """Dummy provider to track call counts for cache testing."""

    def __init__(self) -> None:
        self.quote_calls = 0
        self.history_calls = 0
        self.search_calls = 0
        self.status_calls = 0

    @property
    def name(self) -> str:
        return "dummy"

    async def get_quote(self, symbol: str) -> ProviderQuote:
        self.quote_calls += 1
        return ProviderQuote(
            symbol=symbol,
            price=Decimal("150.00"),
            currency="USD",
            timestamp=datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc),
            change=Decimal("1.50"),
            change_percent=Decimal("1.01"),
        )

    async def get_historical_bars(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        interval: str = "1d",
    ) -> list[ProviderBar]:
        self.history_calls += 1
        return [
            ProviderBar(
                symbol=symbol,
                timestamp=start,
                open=Decimal("148.00"),
                high=Decimal("151.00"),
                low=Decimal("147.50"),
                close=Decimal("150.00"),
                volume=Decimal("1000000"),
            )
        ]

    async def search_instruments(self, query: str) -> list[ProviderInstrument]:
        self.search_calls += 1
        return [
            ProviderInstrument(
                symbol="DUMMY",
                name="Dummy Corp",
                asset_type="equity",
            )
        ]

    async def get_status(self) -> ProviderStatus:
        self.status_calls += 1
        return ProviderStatus(name="dummy", is_active=True, message="OK")


class TestAsyncMemoryCache(unittest.IsolatedAsyncioTestCase):
    """Unit tests for AsyncMemoryCache core data structure and algorithms."""

    async def test_set_and_get_hit(self) -> None:
        cache = AsyncMemoryCache()
        await cache.set("key1", "value1", ttl_seconds=10.0)
        result = await cache.get("key1")
        self.assertEqual(result, "value1")
        self.assertEqual(cache.hits, 1)
        self.assertEqual(cache.misses, 0)

    async def test_get_miss(self) -> None:
        cache = AsyncMemoryCache()
        result = await cache.get("nonexistent")
        self.assertIsNone(result)
        self.assertEqual(cache.hits, 0)
        self.assertEqual(cache.misses, 1)

    async def test_ttl_expiration(self) -> None:
        cache = AsyncMemoryCache()
        await cache.set("temp", "expiring_val", ttl_seconds=0.05)
        # Immediate read succeeds
        self.assertEqual(await cache.get("temp"), "expiring_val")
        # Wait for expiration
        await asyncio.sleep(0.07)
        self.assertIsNone(await cache.get("temp"))
        self.assertGreaterEqual(cache.evictions, 1)

    async def test_capacity_eviction(self) -> None:
        cache = AsyncMemoryCache(max_capacity=3)
        await cache.set("k1", "v1", ttl_seconds=60.0)
        await cache.set("k2", "v2", ttl_seconds=60.0)
        await cache.set("k3", "v3", ttl_seconds=60.0)
        self.assertEqual(cache.size(), 3)

        # 4th key triggers capacity eviction
        await cache.set("k4", "v4", ttl_seconds=60.0)
        self.assertLessEqual(cache.size(), 3)
        self.assertGreaterEqual(cache.evictions, 1)

    async def test_delete_and_clear(self) -> None:
        cache = AsyncMemoryCache()
        await cache.set("item1", "v1", ttl_seconds=60.0)
        self.assertTrue(await cache.delete("item1"))
        self.assertFalse(await cache.delete("item1"))

        await cache.set("a", 1, ttl_seconds=60.0)
        await cache.set("b", 2, ttl_seconds=60.0)
        self.assertEqual(cache.size(), 2)
        await cache.clear()
        self.assertEqual(cache.size(), 0)

    async def test_single_flight_request_coalescing(self) -> None:
        """Concurrent requests for the same key should coalesce into a single execution."""
        cache = AsyncMemoryCache()
        call_count = 0

        async def expensive_factory() -> str:
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.05)
            return "computed_data"

        # Spawn 10 concurrent requests for the exact same key
        tasks = [
            cache.get_or_set("shared_key", expensive_factory, ttl_seconds=10.0)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # All 10 coroutines received the correct result
        for res in results:
            self.assertEqual(res, "computed_data")

        # But factory was invoked exactly once!
        self.assertEqual(call_count, 1)
        self.assertEqual(cache.coalesced, 9)

    async def test_lru_eviction(self) -> None:
        cache = AsyncMemoryCache(max_capacity=2, eviction_policy="lru")
        await cache.set("k1", "v1", ttl_seconds=60.0)
        await cache.set("k2", "v2", ttl_seconds=60.0)
        # Access k1 to make k2 least recently used
        await cache.get("k1")
        # Inserting k3 should evict k2
        await cache.set("k3", "v3", ttl_seconds=60.0)
        self.assertEqual(await cache.get("k1"), "v1")
        self.assertIsNone(await cache.get("k2"))
        self.assertEqual(await cache.get("k3"), "v3")
        self.assertEqual(cache.evictions, 1)

    async def test_lfu_eviction(self) -> None:
        cache = AsyncMemoryCache(max_capacity=2, eviction_policy="lfu")
        await cache.set("k1", "v1", ttl_seconds=60.0)
        await cache.set("k2", "v2", ttl_seconds=60.0)
        # Access k1 multiple times
        for _ in range(4):
            await cache.get("k1")
        # Inserting k3 should evict k2 (lower frequency)
        await cache.set("k3", "v3", ttl_seconds=60.0)
        self.assertEqual(await cache.get("k1"), "v1")
        self.assertIsNone(await cache.get("k2"))
        self.assertEqual(await cache.get("k3"), "v3")

    async def test_fifo_eviction(self) -> None:
        cache = AsyncMemoryCache(max_capacity=2, eviction_policy="fifo")
        await cache.set("k1", "v1", ttl_seconds=60.0)
        await cache.set("k2", "v2", ttl_seconds=60.0)
        # Access k1 heavily
        for _ in range(5):
            await cache.get("k1")
        # In FIFO, k1 was inserted first, so k1 is evicted!
        await cache.set("k3", "v3", ttl_seconds=60.0)
        self.assertIsNone(await cache.get("k1"))
        self.assertEqual(await cache.get("k2"), "v2")
        self.assertEqual(await cache.get("k3"), "v3")

    def test_invalid_eviction_policy(self) -> None:
        with self.assertRaises(ValueError):
            AsyncMemoryCache(eviction_policy="invalid_policy")

    async def test_stale_while_revalidate(self) -> None:
        cache = AsyncMemoryCache()
        await cache.set("temp", "live_data", ttl_seconds=0.05, stale_ttl_seconds=0.5)
        val, is_stale = await cache.get_with_staleness("temp")
        self.assertEqual(val, "live_data")
        self.assertFalse(is_stale)

        # Wait past normal TTL but within stale grace window
        await asyncio.sleep(0.07)
        val, is_stale = await cache.get_with_staleness("temp")
        self.assertEqual(val, "live_data")
        self.assertTrue(is_stale)
        self.assertEqual(cache.stale_hits, 1)

    async def test_clear_by_prefix(self) -> None:
        cache = AsyncMemoryCache()
        await cache.set("quote:AAPL", "q1", 60.0)
        await cache.set("quote:MSFT", "q2", 60.0)
        await cache.set("history:AAPL:1:2:1d", "h1", 60.0)
        self.assertEqual(cache.size(), 3)

        removed = await cache.clear(prefix="quote:")
        self.assertEqual(removed, 2)
        self.assertEqual(cache.size(), 1)
        self.assertIsNone(await cache.get("quote:AAPL"))
        self.assertEqual(await cache.get("history:AAPL:1:2:1d"), "h1")

    async def test_purge_expired(self) -> None:
        cache = AsyncMemoryCache()
        await cache.set("expired_key", "val", ttl_seconds=0.04)
        await cache.set("alive_key", "val", ttl_seconds=60.0)
        await asyncio.sleep(0.06)

        purged = await cache.purge_expired()
        self.assertEqual(purged, 1)
        self.assertEqual(cache.size(), 1)
        self.assertIsNone(await cache.get("expired_key"))
        self.assertEqual(await cache.get("alive_key"), "val")

    async def test_telemetry_and_hit_ratio(self) -> None:
        cache = AsyncMemoryCache()
        await cache.set("k1", "v1", 60.0)
        await cache.get("k1")  # hit
        await cache.get("missing")  # miss
        stats = cache.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["hit_ratio"], 0.5)


class TestCachedMarketDataProvider(unittest.IsolatedAsyncioTestCase):
    """Unit tests for CachedMarketDataProvider proxy decorator."""

    async def test_quote_caching_and_hits(self) -> None:
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(dummy, quote_ttl=10.0)

        # First request -> Cache miss, invokes provider
        q1 = await cached.get_quote("AAPL")
        self.assertEqual(q1.symbol, "AAPL")
        self.assertEqual(dummy.quote_calls, 1)

        # Second request -> Cache hit, provider not called again
        q2 = await cached.get_quote("AAPL")
        self.assertEqual(q2.price, Decimal("150.00"))
        self.assertEqual(dummy.quote_calls, 1)

        # Different symbol -> Cache miss, invokes provider
        q3 = await cached.get_quote("MSFT")
        self.assertEqual(q3.symbol, "MSFT")
        self.assertEqual(dummy.quote_calls, 2)

    async def test_historical_bars_caching(self) -> None:
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(dummy, history_ttl=10.0)
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 10, tzinfo=timezone.utc)

        # First call -> miss
        bars1 = await cached.get_historical_bars("AAPL", start, end, "1d")
        self.assertEqual(len(bars1), 1)
        self.assertEqual(dummy.history_calls, 1)

        # Second call with same parameters -> hit
        bars2 = await cached.get_historical_bars("AAPL", start, end, "1d")
        self.assertEqual(len(bars2), 1)
        self.assertEqual(dummy.history_calls, 1)

    async def test_search_instruments_caching(self) -> None:
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(dummy, search_ttl=10.0)

        res1 = await cached.search_instruments("apple")
        self.assertEqual(len(res1), 1)
        self.assertEqual(dummy.search_calls, 1)

        # Identical query (case-insensitive) -> hit
        res2 = await cached.search_instruments("APPLE")
        self.assertEqual(len(res2), 1)
        self.assertEqual(dummy.search_calls, 1)

        # Empty search returns empty without provider call
        res_empty = await cached.search_instruments("   ")
        self.assertEqual(res_empty, [])
        self.assertEqual(dummy.search_calls, 1)

    async def test_status_bypasses_cache(self) -> None:
        """Provider status check must always execute live without caching."""
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(dummy)

        await cached.get_status()
        await cached.get_status()
        self.assertEqual(dummy.status_calls, 2)

    async def test_cache_disabled_mode(self) -> None:
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(dummy, enabled=False)

        await cached.get_quote("AAPL")
        await cached.get_quote("AAPL")
        self.assertEqual(dummy.quote_calls, 2)

    async def test_stats_and_clear(self) -> None:
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(dummy, quote_ttl=10.0)

        await cached.get_quote("AAPL")
        await cached.get_quote("AAPL")
        stats = cached.get_stats()
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["misses"], 1)
        self.assertEqual(stats["size"], 1)

        await cached.clear_cache()
        self.assertEqual(cached.get_stats()["size"], 0)

    async def test_graceful_degradation_on_provider_error(self) -> None:
        from app.core.errors import ProviderUnavailableError

        class FailingProvider(DummyProvider):
            def __init__(self) -> None:
                super().__init__()
                self.should_fail = False

            async def get_quote(self, symbol: str) -> ProviderQuote:
                if self.should_fail:
                    raise ProviderUnavailableError("Simulated upstream provider outage")
                return await super().get_quote(symbol)

        failing = FailingProvider()
        cached = CachedMarketDataProvider(failing, quote_ttl=0.05, stale_grace_ttl=5.0)

        # 1. First fetch primes the cache
        q1 = await cached.get_quote("AAPL")
        self.assertEqual(q1.price, Decimal("150.00"))
        self.assertFalse(q1.is_stale)

        # 2. Wait for quote_ttl to expire, then trigger provider failure
        await asyncio.sleep(0.07)
        failing.should_fail = True

        # 3. Should not crash! Should gracefully return stale quote
        q2 = await cached.get_quote("AAPL")
        self.assertEqual(q2.price, Decimal("150.00"))
        self.assertTrue(q2.is_stale)
        self.assertEqual(cached.cache.stale_hits, 1)

    async def test_tier2_persistence_fallback(self) -> None:
        from app.core.errors import ProviderUnavailableError

        class BrokenProvider(DummyProvider):
            async def get_quote(self, symbol: str) -> ProviderQuote:
                raise ProviderUnavailableError("Total provider downtime")

        persisted_quote = ProviderQuote(
            symbol="AAPL",
            price=Decimal("182.25"),
            currency="USD",
            timestamp=datetime(2026, 4, 25, 12, 0, 0, tzinfo=timezone.utc),
        )

        def db_fallback(symbol: str) -> Optional[ProviderQuote]:
            if symbol == "AAPL":
                return persisted_quote
            return None

        cached = CachedMarketDataProvider(BrokenProvider(), db_fallback_fn=db_fallback)

        # In-memory has no prior entry, provider fails, Tier-2 persistence fallback is returned!
        q = await cached.get_quote("AAPL")
        self.assertEqual(q.symbol, "AAPL")
        self.assertEqual(q.price, Decimal("182.25"))
        self.assertTrue(q.is_stale)

    async def test_differentiated_ttls_and_telemetry(self) -> None:
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(
            dummy,
            quote_ttl=12.0,
            history_ttl=240.0,
            search_ttl=480.0,
            asset_ttl=1200.0,
            stale_grace_ttl=3600.0,
        )
        stats = cached.get_stats()
        self.assertTrue(stats["enabled"])
        self.assertEqual(stats["ttl_config"]["quote_ttl"], 12.0)
        self.assertEqual(stats["ttl_config"]["history_ttl"], 240.0)
        self.assertEqual(stats["ttl_config"]["search_ttl"], 480.0)
        self.assertEqual(stats["ttl_config"]["asset_ttl"], 1200.0)
        self.assertEqual(stats["ttl_config"]["stale_grace_ttl"], 3600.0)

    async def test_clear_cache_prefix(self) -> None:
        dummy = DummyProvider()
        cached = CachedMarketDataProvider(dummy, quote_ttl=60.0, search_ttl=60.0)

        await cached.get_quote("AAPL")
        await cached.search_instruments("apple")
        self.assertEqual(cached.cache.size(), 2)

        # Clear only quotes
        removed = await cached.clear_cache(prefix="quote:")
        self.assertEqual(removed, 1)
        self.assertEqual(cached.cache.size(), 1)


class TestMarketDataServiceWithCache(unittest.IsolatedAsyncioTestCase):
    """Unit tests verifying MarketDataService integration with caching layer."""

    async def test_service_wraps_provider_with_cache_by_default(self) -> None:
        dummy = DummyProvider()
        service = MarketDataService(provider=dummy, enable_cache=True)
        self.assertIsInstance(service.provider, CachedMarketDataProvider)

        # First quote triggers provider
        await service.get_quote("AAPL")
        self.assertEqual(dummy.quote_calls, 1)

        # Second quote uses cache
        await service.get_quote("AAPL")
        self.assertEqual(dummy.quote_calls, 1)

        stats = service.get_cache_stats()
        self.assertIsNotNone(stats)
        self.assertEqual(stats["hits"], 1)

    async def test_service_disables_cache_when_requested(self) -> None:
        dummy = DummyProvider()
        service = MarketDataService(provider=dummy, enable_cache=False)
        self.assertEqual(service.provider, dummy)
        self.assertIsNone(service.get_cache_stats())

        await service.get_quote("AAPL")
        await service.get_quote("AAPL")
        self.assertEqual(dummy.quote_calls, 2)

    async def test_service_clear_cache_prefix_and_purge(self) -> None:
        dummy = DummyProvider()
        service = MarketDataService(provider=dummy, enable_cache=True)

        await service.get_quote("AAPL")
        self.assertEqual(service.get_cache_stats()["size"], 1)

        # Purge when unexpired returns 0
        purged = await service.purge_expired_cache()
        self.assertEqual(purged, 0)

        # Clear prefix
        removed = await service.clear_cache(prefix="quote:")
        self.assertEqual(removed, 1)
        self.assertEqual(service.get_cache_stats()["size"], 0)
