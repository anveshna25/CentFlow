import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Individual in-memory cache entry with expiration timestamp,
    access metrics, logical sequence ordering, and stale-while-revalidate grace period.
    """

    value: T
    expires_at: float
    created_at: float
    last_accessed_at: float
    access_count: int = 1
    stale_until: float = 0.0
    access_seq: int = 0
    created_seq: int = 0

    def is_expired(self, now: float) -> bool:
        """Check if entry has passed its TTL expiration timestamp."""
        return now >= self.expires_at

    def is_stale(self, now: float) -> bool:
        """Check if entry is expired but still within stale grace window."""
        if self.stale_until > 0.0:
            return self.expires_at <= now < self.stale_until
        return False

    def is_dead(self, now: float) -> bool:
        """Check if entry is past both its TTL and stale grace window."""
        if self.stale_until > 0.0:
            return now >= self.stale_until
        return now >= self.expires_at

    def touch(self, now: float, seq: int) -> None:
        """Record an access hit for LRU and LFU eviction algorithms."""
        self.last_accessed_at = now
        self.access_count += 1
        self.access_seq = seq


class AsyncMemoryCache:
    """Thread-safe, asynchronous in-memory cache with differentiated TTL expiration,
    pluggable eviction policies (LRU, LFU, FIFO), maximum capacity management,
    single-flight request coalescing, and stale-while-revalidate graceful degradation.
    """

    VALID_POLICIES = ("lru", "lfu", "fifo")

    def __init__(self, max_capacity: int = 1000, eviction_policy: str = "lru") -> None:
        policy = eviction_policy.lower().strip()
        if policy not in self.VALID_POLICIES:
            raise ValueError(
                f"Invalid eviction policy '{eviction_policy}'. Must be one of: {', '.join(self.VALID_POLICIES)}"
            )

        self._max_capacity = max(1, int(max_capacity))
        self._eviction_policy = policy
        self._store: dict[str, CacheEntry[Any]] = {}
        self._in_flight: dict[str, tuple[asyncio.Future[Any], int]] = {}
        self._lock = asyncio.Lock()
        self._seq = 0

        # Telemetry / metrics counters
        self._hits = 0
        self._misses = 0
        self._stale_hits = 0
        self._evictions = 0
        self._coalesced = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def stale_hits(self) -> int:
        return self._stale_hits

    @property
    def evictions(self) -> int:
        return self._evictions

    @property
    def coalesced(self) -> int:
        return self._coalesced

    @property
    def max_capacity(self) -> int:
        return self._max_capacity

    @property
    def eviction_policy(self) -> str:
        return self._eviction_policy

    @property
    def hit_ratio(self) -> float:
        total = self._hits + self._stale_hits + self._misses
        if total == 0:
            return 0.0
        return round((self._hits + self._stale_hits) / total, 4)

    def size(self) -> int:
        """Current number of items in cache store."""
        return len(self._store)

    def get_stats(self) -> dict[str, Any]:
        """Return snapshot dictionary of cache metrics."""
        return {
            "size": self.size(),
            "max_capacity": self._max_capacity,
            "eviction_policy": self._eviction_policy,
            "hits": self._hits,
            "misses": self._misses,
            "stale_hits": self._stale_hits,
            "evictions": self._evictions,
            "coalesced": self._coalesced,
            "hit_ratio": self.hit_ratio,
        }

    async def get(self, key: str) -> Optional[Any]:
        """Retrieve value from cache if present and unexpired."""
        val, _ = await self.get_with_staleness(key)
        return val

    async def get_with_staleness(self, key: str) -> tuple[Optional[Any], bool]:
        """Retrieve value from cache along with staleness indicator.

        Returns:
            (value, False) if present and fresh (within TTL)
            (value, True) if expired but within stale grace window
            (None, False) if missing or dead (past stale grace window)
        """
        now = time.monotonic()
        async with self._lock:
            entry = self._store.get(key)
            if entry is not None:
                if entry.is_dead(now):
                    del self._store[key]
                    self._evictions += 1
                    self._misses += 1
                    return None, False
                self._seq += 1
                if entry.is_expired(now):
                    entry.touch(now, self._seq)
                    self._stale_hits += 1
                    return entry.value, True
                entry.touch(now, self._seq)
                self._hits += 1
                return entry.value, False
            self._misses += 1
            return None, False

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: float,
        stale_ttl_seconds: float = 0.0,
    ) -> None:
        """Store value with specified TTL expiration and optional stale grace window in seconds."""
        now = time.monotonic()
        expires_at = now + max(0.0, float(ttl_seconds))
        stale_until = (
            expires_at + max(0.0, float(stale_ttl_seconds))
            if stale_ttl_seconds > 0.0
            else expires_at
        )

        async with self._lock:
            # Capacity management: evict dead/oldest if at capacity
            if len(self._store) >= self._max_capacity and key not in self._store:
                self._evict_over_capacity(now)

            self._seq += 1
            seq = self._seq
            existing = self._store.get(key)
            access_count = (existing.access_count + 1) if existing is not None else 1
            created_seq = existing.created_seq if existing is not None else seq

            self._store[key] = CacheEntry(
                value=value,
                expires_at=expires_at,
                created_at=now if existing is None else existing.created_at,
                last_accessed_at=now,
                access_count=access_count,
                stale_until=stale_until,
                access_seq=seq,
                created_seq=created_seq,
            )

    async def delete(self, key: str) -> bool:
        """Delete specific key from cache."""
        async with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    async def clear(self, prefix: Optional[str] = None) -> int:
        """Remove entries matching prefix, or remove all entries if prefix is None.

        Returns:
            Count of removed entries.
        """
        async with self._lock:
            if prefix is None:
                count = len(self._store)
                self._store.clear()
                self._in_flight.clear()
                return count

            keys_to_remove = [k for k in self._store.keys() if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]
            # Also clean matching in-flight tracking
            in_flight_to_remove = [k for k in self._in_flight.keys() if k.startswith(prefix)]
            for k in in_flight_to_remove:
                self._in_flight.pop(k, None)
            return len(keys_to_remove)

    async def purge_expired(self) -> int:
        """Manually purge all expired/dead keys from store."""
        now = time.monotonic()
        purged = 0
        async with self._lock:
            expired_keys = [k for k, v in self._store.items() if v.is_dead(now)]
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
        stale_ttl_seconds: float = 0.0,
        fallback_on_error: bool = True,
    ) -> T:
        """Retrieve cached value or compute using factory with request coalescing
        and optional stale-while-revalidate fallback on provider error.
        """
        now = time.monotonic()

        # Step 1: Check fast-path in cache
        async with self._lock:
            entry = self._store.get(key)
            if entry is not None and not entry.is_expired(now):
                self._seq += 1
                entry.touch(now, self._seq)
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
            await self.set(
                key=key,
                value=val,
                ttl_seconds=ttl_seconds,
                stale_ttl_seconds=stale_ttl_seconds,
            )
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
                leader_fut = item[0] if item is not None else None
                waiters = item[1] if item is not None else 0

                # SWR Graceful Degradation: If fallback is enabled and we have a stale entry
                if fallback_on_error:
                    stale_entry = self._store.get(key)
                    if stale_entry is not None:
                        self._seq += 1
                        stale_entry.touch(now, self._seq)
                        self._stale_hits += 1
                        fallback_val = stale_entry.value
                        if leader_fut is not None and not leader_fut.done():
                            leader_fut.set_result(fallback_val)
                        return fallback_val

                # If no fallback was possible, notify waiters of exception and raise
                if leader_fut is not None and not leader_fut.done():
                    if waiters > 0:
                        leader_fut.set_exception(exc)
                    else:
                        leader_fut.cancel()
            raise

    def _evict_over_capacity(self, now: float) -> None:
        """Internal helper to evict dead entries or victims based on eviction policy."""
        # 1. First, evict any dead entries
        dead = [k for k, v in self._store.items() if v.is_dead(now)]
        for k in dead:
            del self._store[k]
            self._evictions += 1

        # 2. If still at/over capacity, evict based on policy
        while len(self._store) >= self._max_capacity and self._store:
            if self._eviction_policy == "lfu":
                victim = min(
                    self._store.keys(),
                    key=lambda k: (self._store[k].access_count, self._store[k].access_seq),
                )
            elif self._eviction_policy == "fifo":
                victim = min(
                    self._store.keys(),
                    key=lambda k: self._store[k].created_seq,
                )
            else:  # default "lru"
                victim = min(
                    self._store.keys(),
                    key=lambda k: self._store[k].access_seq,
                )
            del self._store[victim]
            self._evictions += 1
