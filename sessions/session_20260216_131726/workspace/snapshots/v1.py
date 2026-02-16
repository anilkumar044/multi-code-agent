"""
Thread-safe LRU Cache with TTL Expiry and Async Support.

Provides a doubly-linked list + hash map LRU eviction policy,
per-entry TTL expiration, thread safety via RLock, async-compatible
get/set methods (async wrappers around the sync core), and
hit/miss statistics tracking.
"""

import asyncio
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Generic, Hashable, Optional, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


@dataclass
class CacheStats:
    """Snapshot of cache hit/miss counters."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expired: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Fraction of lookups that were cache hits (0.0 if no lookups)."""
        return self.hits / self.total if self.total > 0 else 0.0

    def __repr__(self) -> str:
        return (
            f"CacheStats(hits={self.hits}, misses={self.misses}, "
            f"evictions={self.evictions}, expired={self.expired}, "
            f"hit_rate={self.hit_rate:.2%})"
        )


@dataclass
class _Entry:
    """Internal cache entry storing value, expiry timestamp, and access order."""
    value: Any
    # Absolute expiry time in seconds since epoch; None means no expiry.
    expires_at: Optional[float]

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.monotonic() >= self.expires_at


class LRUCache(Generic[K, V]):
    """
    Thread-safe Least-Recently-Used (LRU) cache with optional per-entry TTL.

    Parameters
    ----------
    capacity : int
        Maximum number of entries. Must be >= 1.
    default_ttl : float | None
        Default time-to-live in seconds for entries that do not specify one.
        ``None`` (default) means entries never expire unless explicitly set.

    Thread safety
    -------------
    All public synchronous methods are protected by a reentrant lock so the
    cache can be shared across threads without external synchronisation.

    Async support
    -------------
    ``aget`` and ``aset`` are thin async wrappers that call the synchronous
    core on the running event loop's thread-pool executor, making them safe
    to ``await`` from async code without blocking the event loop.

    Examples
    --------
    >>> cache: LRUCache[str, int] = LRUCache(capacity=3, default_ttl=60)
    >>> cache.set("a", 1)
    >>> cache.get("a")
    1
    >>> cache.get("missing")  # returns None
    >>> cache.stats()
    CacheStats(hits=1, misses=1, ...)
    """

    def __init__(self, capacity: int, default_ttl: Optional[float] = None) -> None:
        if capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {capacity}")
        if default_ttl is not None and default_ttl <= 0:
            raise ValueError(f"default_ttl must be > 0, got {default_ttl}")

        self._capacity = capacity
        self._default_ttl = default_ttl
        # OrderedDict preserves insertion/move order; last = most recently used.
        self._cache: OrderedDict[K, _Entry] = OrderedDict()
        self._lock = threading.RLock()

        # Statistics counters (protected by the same lock)
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expired = 0

    # ------------------------------------------------------------------
    # Public synchronous API
    # ------------------------------------------------------------------

    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """
        Retrieve *key* from the cache.

        Returns *default* (``None`` by default) on cache miss or if the
        entry has expired. Expired entries are lazily removed on access.

        Updates the LRU order on hit so *key* becomes the most-recently used.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return default

            if entry.is_expired():
                # Lazy expiry: remove stale entry and count as miss.
                del self._cache[key]
                self._expired += 1
                self._misses += 1
                return default

            # Move to end (most recently used position).
            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value  # type: ignore[return-value]

    def set(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """
        Insert or update *key* -> *value*.

        Parameters
        ----------
        key : K
            Cache key (must be hashable).
        value : V
            Value to store.
        ttl : float | None
            Per-entry TTL in seconds. Overrides ``default_ttl`` when given.
            Pass ``0`` or a negative number to get an immediate expiry
            (the entry will be expired on the next access).
            ``None`` falls back to ``default_ttl``; if that is also ``None``
            the entry never expires.
        """
        with self._lock:
            effective_ttl = ttl if ttl is not None else self._default_ttl
            if effective_ttl is not None:
                expires_at = time.monotonic() + effective_ttl
            else:
                expires_at = None

            if key in self._cache:
                # Update existing entry and promote to MRU position.
                self._cache[key] = _Entry(value=value, expires_at=expires_at)
                self._cache.move_to_end(key)
            else:
                # Evict LRU entry if at capacity.
                if len(self._cache) >= self._capacity:
                    self._cache.popitem(last=False)  # Remove oldest (LRU)
                    self._evictions += 1
                self._cache[key] = _Entry(value=value, expires_at=expires_at)

    def delete(self, key: K) -> bool:
        """
        Remove *key* from the cache.

        Returns ``True`` if the key existed (and was removed), ``False`` otherwise.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Remove all entries from the cache (statistics are preserved)."""
        with self._lock:
            self._cache.clear()

    def contains(self, key: K) -> bool:
        """
        Return ``True`` if *key* is present and not expired.

        Does **not** update LRU order or statistics.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                del self._cache[key]
                self._expired += 1
                return False
            return True

    def stats(self) -> CacheStats:
        """Return a snapshot of the current hit/miss/eviction/expired counters."""
        with self._lock:
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                evictions=self._evictions,
                expired=self._expired,
            )

    def reset_stats(self) -> None:
        """Reset all statistics counters to zero."""
        with self._lock:
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expired = 0

    def size(self) -> int:
        """Return the number of entries currently in the cache (including potentially expired ones)."""
        with self._lock:
            return len(self._cache)

    @property
    def capacity(self) -> int:
        """Maximum number of entries this cache can hold."""
        return self._capacity

    # ------------------------------------------------------------------
    # Async API (thin wrappers, run sync core in executor)
    # ------------------------------------------------------------------

    async def aget(self, key: K, default: Optional[V] = None) -> Optional[V]:
        """
        Async version of get().

        Runs the synchronous implementation in the default thread-pool
        executor so the event loop is not blocked.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.get, key, default)

    async def aset(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """
        Async version of set().

        Runs the synchronous implementation in the default thread-pool
        executor so the event loop is not blocked.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: self.set(key, value, ttl))

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return self.size()

    def __contains__(self, key: object) -> bool:
        return self.contains(key)  # type: ignore[arg-type]

    def __repr__(self) -> str:
        return (
            f"LRUCache(capacity={self._capacity}, size={self.size()}, "
            f"default_ttl={self._default_ttl})"
        )


# ---------------------------------------------------------------------------
# Usage example
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    print("=== Synchronous demo ===")
    cache: LRUCache[str, int] = LRUCache(capacity=3, default_ttl=5.0)

    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    print(f"get a={cache.get('a')}")   # hit
    print(f"get d={cache.get('d')}")   # miss

    # Eviction: capacity=3, adding 'd' evicts LRU key ('b' since 'a' was just accessed)
    cache.set("d", 4)
    print(f"get b={cache.get('b')}")   # miss (evicted)
    print(f"get c={cache.get('c')}")   # hit
    print(f"get d={cache.get('d')}")   # hit

    print(cache.stats())
    print(cache)

    print("\n=== TTL expiry demo ===")
    short_cache: LRUCache[str, str] = LRUCache(capacity=10)
    short_cache.set("temp", "hello", ttl=0.05)  # 50 ms TTL
    print(f"before expiry: {short_cache.get('temp')}")
    time.sleep(0.1)
    print(f"after expiry:  {short_cache.get('temp')}")
    print(short_cache.stats())

    print("\n=== Async demo ===")

    async def async_demo() -> None:
        acache: LRUCache[str, str] = LRUCache(capacity=5, default_ttl=10.0)
        await acache.aset("key1", "value1")
        await acache.aset("key2", "value2")
        v = await acache.aget("key1")
        print(f"async get key1={v}")
        print(acache.stats())

    asyncio.run(async_demo())
