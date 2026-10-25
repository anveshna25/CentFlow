import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Individual in-memory cache entry with expiration timestamp."""

    value: T
    expires_at: float
    created_at: float

    def is_expired(self, now: float) -> bool:
        """Check if entry has passed its TTL expiration timestamp."""
        return now >= self.expires_at


class AsyncMemoryCache:
    """Thread-safe, asynchronous in-memory cache with TTL expiration,
    maximum capacity capping, and single-flight request coalescing.
    """

    def __init__(self, max_capacity: int = 1000) -> None:
        self._max_capacity = max_capacity
        self._store: dict[str, CacheEntry[Any]] = {}
        self._in_flight: dict[str, tuple[asyncio.Future[Any], int]] = {}
        self._lock = asyncio.Lock()

        # Telemetry / metrics counters
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._coalesced = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def evictions(self) -> int:
        return self._evictions

    @property
    def coalesced(self) -> int:
        return self._coalesced

    def size(self) -> int:
        """Current number of items in cache store."""
        return len(self._store)

    def get_stats(self) -> dict[str, int]:
        """Return snapshot dictionary of cache metrics."""
        return {
            "size": self.size(),
            "max_capacity": self._max_capacity,
            "hits": self._hits,
            "misses": self._misses,
            "evictions": self._evictions,
            "coalesced": self._coalesced,
        }

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache if present and unexpired."""
        now = time.monotonic()
        async with self._lock:
            entry = self._store.get(key)
            if entry is not None:
                if entry.is_expired(now):
                    del self._store[key]
                    self._evictions += 1
                    self._misses += 1
                    return None
                self._hits += 1
                return entry.value
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        """Store value with specified TTL expiration in seconds."""
        now = time.monotonic()
        expires_at = now + max(0.0, float(ttl_seconds))

        async with self._lock:
            # Capacity management: evict expired or oldest
            if len(self._store) >= self._max_capacity and key not in self._store:
                self._evict_over_capacity(now)

            self._store[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
                created_at=now,
            )

    async def delete(self, key: str) -> bool:
        """Delete specific key from cache."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def clear(self) -> None:
        """Remove all entries and reset store."""
        async with self._lock:
            self._store.clear()
            self._in_flight.clear()

    async def purge_expired(self) -> int:
        """Manually purge all expired keys from store."""
        now = time.monotonic()
        purged = 0
        async with self._lock:
            expired_keys = [k for k, v in self._store.items() if v.is_expired(now)]
            for k in expired_keys:
                del self._store[k]
                purged += 1
            self._evictions += purged
        return purged

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Awaitable[T]],
        ttl_seconds: float,
    ) -> T:
        """Retrieve cached value or compute using factory with request coalescing.

        If multiple concurrent coroutines request the same missing key simultaneously,
        only one execution of factory() is triggered while others await the single flight.
        """
        now = time.monotonic()

        # Step 1: Check fast-path in cache
        async with self._lock:
            entry = self._store.get(key)
            if entry is not None and not entry.is_expired(now):
                self._hits += 1
                return entry.value

            # Step 2: Check if another task is already calculating this key (Single-flight)
            if key in self._in_flight:
                self._coalesced += 1
                fut, waiters = self._in_flight[key]
                self._in_flight[key] = (fut, waiters + 1)
            else:
                loop = asyncio.get_running_loop()
                fut = loop.create_future()
                self._in_flight[key] = (fut, 0)
                fut = None  # Leader task will run factory

        # Follower coroutine: await in-flight future
        if fut is not None:
            return await fut

        # Leader coroutine: execute factory and notify waiters
        try:
            val = await factory()
            await self.set(key, val, ttl_seconds)
            self._misses += 1

            async with self._lock:
                item = self._in_flight.pop(key, None)
                if item is not None:
                    leader_fut, _ = item
                    if not leader_fut.done():
                        leader_fut.set_result(val)
            return val
        except BaseException as exc:
            async with self._lock:
                item = self._in_flight.pop(key, None)
                if item is not None:
                    leader_fut, waiters = item
                    if not leader_fut.done():
                        if waiters > 0:
                            leader_fut.set_exception(exc)
                        else:
                            leader_fut.cancel()
            raise

    def _evict_over_capacity(self, now: float) -> None:
        """Internal helper to evict expired or oldest items when max capacity reached."""
        # 1. Evict any expired entries
        expired = [k for k, v in self._store.items() if v.is_expired(now)]
        for k in expired:
            del self._store[k]
            self._evictions += 1

        # 2. If still over capacity, evict oldest entry
        if len(self._store) >= self._max_capacity:
            oldest_key = min(self._store.keys(), key=lambda k: self._store[k].created_at)
            del self._store[oldest_key]
            self._evictions += 1
