"""
Comprehensive pytest test suite for the LRUCache implementation in solution.py.
"""

import asyncio
import threading
import time

import pytest

from solution import CacheStats, LRUCache


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_valid_capacity_creates_cache(self):
        cache = LRUCache(capacity=10)
        assert cache.capacity == 10
        assert len(cache) == 0

    def test_capacity_one_is_valid(self):
        cache = LRUCache(capacity=1)
        assert cache.capacity == 1

    def test_invalid_capacity_zero_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            LRUCache(capacity=0)

    def test_invalid_capacity_negative_raises(self):
        with pytest.raises(ValueError, match="capacity"):
            LRUCache(capacity=-5)

    def test_default_ttl_none(self):
        cache = LRUCache(capacity=5)
        cache.set("k", "v")
        time.sleep(0.05)
        assert cache.get("k") == "v"  # never expires

    def test_invalid_default_ttl_zero_raises(self):
        with pytest.raises(ValueError, match="default_ttl"):
            LRUCache(capacity=5, default_ttl=0)

    def test_invalid_default_ttl_negative_raises(self):
        with pytest.raises(ValueError, match="default_ttl"):
            LRUCache(capacity=5, default_ttl=-1.0)

    def test_valid_default_ttl(self):
        cache = LRUCache(capacity=5, default_ttl=60.0)
        assert cache.capacity == 5

    def test_repr_contains_capacity_and_size(self):
        cache = LRUCache(capacity=5)
        r = repr(cache)
        assert "5" in r
        assert "LRUCache" in r


# ---------------------------------------------------------------------------
# Basic get / set
# ---------------------------------------------------------------------------

class TestGetSet:
    def test_set_and_get_returns_value(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("key", 42)
        assert cache.get("key") == 42

    def test_get_missing_returns_none(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        assert cache.get("missing") is None

    def test_get_missing_with_default(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        assert cache.get("missing", -1) == -1

    def test_set_overwrites_existing_value(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("key", 1)
        cache.set("key", 2)
        assert cache.get("key") == 2
        assert len(cache) == 1  # still one entry

    def test_set_none_value(self):
        cache: LRUCache[str, None] = LRUCache(capacity=5)
        cache.set("key", None)
        # get returns None for both missing and None-valued keys;
        # use contains to distinguish
        assert cache.contains("key")

    def test_various_key_types(self):
        cache: LRUCache = LRUCache(capacity=10)
        cache.set(1, "int key")
        cache.set((1, 2), "tuple key")
        cache.set("str", "string key")
        assert cache.get(1) == "int key"
        assert cache.get((1, 2)) == "tuple key"
        assert cache.get("str") == "string key"


# ---------------------------------------------------------------------------
# LRU eviction
# ---------------------------------------------------------------------------

class TestLRUEviction:
    def test_exceeding_capacity_evicts_lru(self):
        cache: LRUCache[str, int] = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Access 'a' and 'b' to make 'c' the LRU
        cache.get("a")
        cache.get("b")
        cache.set("d", 4)  # 'c' should be evicted
        assert cache.get("c") is None
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("d") == 4

    def test_capacity_one_always_evicts_previous(self):
        cache: LRUCache[str, int] = LRUCache(capacity=1)
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.get("a") is None
        assert cache.get("b") == 2

    def test_update_existing_key_moves_to_mru(self):
        cache: LRUCache[str, int] = LRUCache(capacity=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        # Update 'a' — it should become MRU; 'b' becomes LRU
        cache.set("a", 10)
        cache.set("d", 4)  # 'b' should be evicted
        assert cache.get("b") is None
        assert cache.get("a") == 10
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_eviction_increments_counter(self):
        cache: LRUCache[str, int] = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # evicts 'a'
        assert cache.stats().evictions == 1
        cache.set("d", 4)  # evicts 'b'
        assert cache.stats().evictions == 2

    def test_size_never_exceeds_capacity(self):
        cache: LRUCache[int, int] = LRUCache(capacity=5)
        for i in range(20):
            cache.set(i, i)
        assert len(cache) <= 5


# ---------------------------------------------------------------------------
# TTL expiry
# ---------------------------------------------------------------------------

class TestTTLExpiry:
    def test_entry_accessible_before_ttl(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5)
        cache.set("k", "v", ttl=10.0)
        assert cache.get("k") == "v"

    def test_entry_expired_after_ttl(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5)
        cache.set("k", "v", ttl=0.05)
        time.sleep(0.1)
        assert cache.get("k") is None

    def test_expiry_counted_in_stats(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5)
        cache.set("k", "v", ttl=0.05)
        time.sleep(0.1)
        cache.get("k")
        s = cache.stats()
        assert s.expired == 1
        assert s.misses == 1

    def test_default_ttl_applied_to_entries(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5, default_ttl=0.05)
        cache.set("k", "v")
        time.sleep(0.1)
        assert cache.get("k") is None

    def test_per_entry_ttl_overrides_default(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5, default_ttl=0.05)
        cache.set("k", "v", ttl=60.0)  # long TTL overrides short default
        time.sleep(0.1)
        assert cache.get("k") == "v"

    def test_expired_entry_removed_lazily(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5)
        cache.set("k", "v", ttl=0.05)
        assert len(cache) == 1
        time.sleep(0.1)
        cache.get("k")  # triggers lazy removal
        assert len(cache) == 0

    def test_contains_returns_false_for_expired(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5)
        cache.set("k", "v", ttl=0.05)
        time.sleep(0.1)
        assert not cache.contains("k")

    def test_update_resets_ttl(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5)
        cache.set("k", "v", ttl=0.1)
        time.sleep(0.06)
        # Refresh with longer TTL before expiry
        cache.set("k", "v2", ttl=10.0)
        time.sleep(0.1)
        assert cache.get("k") == "v2"


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

class TestStatistics:
    def test_initial_stats_all_zero(self):
        cache = LRUCache(capacity=5)
        s = cache.stats()
        assert s.hits == 0
        assert s.misses == 0
        assert s.evictions == 0
        assert s.expired == 0

    def test_hit_increments_hits(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        cache.get("k")
        assert cache.stats().hits == 1

    def test_miss_increments_misses(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.get("missing")
        assert cache.stats().misses == 1

    def test_hit_rate_calculation(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        cache.get("k")   # hit
        cache.get("k")   # hit
        cache.get("x")   # miss
        s = cache.stats()
        assert s.total == 3
        assert abs(s.hit_rate - 2 / 3) < 1e-9

    def test_hit_rate_zero_when_no_lookups(self):
        cache = LRUCache(capacity=5)
        assert cache.stats().hit_rate == 0.0

    def test_reset_stats_clears_all_counters(self):
        cache: LRUCache[str, int] = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # eviction
        cache.get("b")     # hit
        cache.get("x")     # miss
        cache.reset_stats()
        s = cache.stats()
        assert s.hits == 0
        assert s.misses == 0
        assert s.evictions == 0
        assert s.expired == 0

    def test_stats_snapshot_is_independent(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        s1 = cache.stats()
        cache.get("k")
        s2 = cache.stats()
        # s1 should not change after more operations
        assert s1.hits == 0
        assert s2.hits == 1

    def test_cache_stats_repr(self):
        s = CacheStats(hits=5, misses=3, evictions=1, expired=0)
        r = repr(s)
        assert "hits=5" in r
        assert "misses=3" in r


# ---------------------------------------------------------------------------
# Delete / Clear / Contains
# ---------------------------------------------------------------------------

class TestDeleteClearContains:
    def test_delete_existing_key_returns_true(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_delete_missing_key_returns_false(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        assert cache.delete("missing") is False

    def test_clear_removes_all_entries(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert len(cache) == 0
        assert cache.get("a") is None

    def test_clear_preserves_stats(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        cache.get("k")
        cache.clear()
        assert cache.stats().hits == 1

    def test_contains_true_for_existing(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        assert cache.contains("k") is True

    def test_contains_false_for_missing(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        assert cache.contains("k") is False

    def test_in_operator_uses_contains(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        assert "k" in cache
        assert "missing" not in cache


# ---------------------------------------------------------------------------
# Async API
# ---------------------------------------------------------------------------

class TestAsyncAPI:
    def test_async_set_and_get(self):
        async def _run():
            cache: LRUCache[str, int] = LRUCache(capacity=5)
            await cache.aset("key", 99)
            result = await cache.aget("key")
            assert result == 99

        asyncio.run(_run())

    def test_async_get_miss_returns_none(self):
        async def _run():
            cache: LRUCache[str, int] = LRUCache(capacity=5)
            result = await cache.aget("missing")
            assert result is None

        asyncio.run(_run())

    def test_async_get_with_default(self):
        async def _run():
            cache: LRUCache[str, int] = LRUCache(capacity=5)
            result = await cache.aget("missing", -1)
            assert result == -1

        asyncio.run(_run())

    def test_async_stats_updated(self):
        async def _run():
            cache: LRUCache[str, int] = LRUCache(capacity=5)
            await cache.aset("k", 1)
            await cache.aget("k")   # hit
            await cache.aget("x")   # miss
            s = cache.stats()
            assert s.hits == 1
            assert s.misses == 1

        asyncio.run(_run())

    def test_async_ttl(self):
        async def _run():
            cache: LRUCache[str, str] = LRUCache(capacity=5)
            await cache.aset("k", "v", ttl=0.05)
            await asyncio.sleep(0.1)
            result = await cache.aget("k")
            assert result is None

        asyncio.run(_run())

    def test_async_concurrent_sets(self):
        async def _run():
            cache: LRUCache[int, int] = LRUCache(capacity=100)
            tasks = [cache.aset(i, i * 2) for i in range(50)]
            await asyncio.gather(*tasks)
            # All keys should be present (capacity not exceeded)
            for i in range(50):
                assert await cache.aget(i) == i * 2

        asyncio.run(_run())

    def test_async_run_in_executor_does_not_block(self):
        """Ensure aset/aget can be gathered concurrently."""
        async def _run():
            cache: LRUCache[str, str] = LRUCache(capacity=10)
            await asyncio.gather(
                cache.aset("a", "1"),
                cache.aset("b", "2"),
                cache.aset("c", "3"),
            )
            results = await asyncio.gather(
                cache.aget("a"),
                cache.aget("b"),
                cache.aget("c"),
            )
            assert set(results) == {"1", "2", "3"}

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:
    def test_concurrent_sets_no_data_race(self):
        cache: LRUCache[int, int] = LRUCache(capacity=1000)
        errors = []

        def worker(start: int) -> None:
            try:
                for i in range(start, start + 100):
                    cache.set(i, i)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i * 100,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(cache) <= 1000

    def test_concurrent_get_set_mixed(self):
        cache: LRUCache[str, int] = LRUCache(capacity=50)
        for i in range(50):
            cache.set(f"key{i}", i)

        errors = []

        def reader():
            try:
                for _ in range(200):
                    cache.get(f"key{_ % 50}")
            except Exception as exc:
                errors.append(exc)

        def writer():
            try:
                for i in range(200):
                    cache.set(f"key{i % 50}", i)
            except Exception as exc:
                errors.append(exc)

        threads = (
            [threading.Thread(target=reader) for _ in range(5)]
            + [threading.Thread(target=writer) for _ in range(5)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_stats_consistent_under_concurrency(self):
        """Total hits + misses == total get calls regardless of threading."""
        cache: LRUCache[int, int] = LRUCache(capacity=10)
        for i in range(10):
            cache.set(i, i)

        get_calls = 1000
        hits_and_misses = []

        def worker():
            for i in range(get_calls // 10):
                cache.get(i % 20)  # 10 will hit, 10 will miss

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        s = cache.stats()
        assert s.hits + s.misses == get_calls


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_cache_operations(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        assert cache.get("k") is None
        assert cache.delete("k") is False
        assert not cache.contains("k")
        assert len(cache) == 0

    def test_large_number_of_items_respects_capacity(self):
        capacity = 100
        cache: LRUCache[int, int] = LRUCache(capacity=capacity)
        for i in range(10_000):
            cache.set(i, i)
        assert len(cache) == capacity

    def test_repeated_gets_dont_change_size(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        for _ in range(100):
            cache.get("k")
        assert len(cache) == 1

    def test_set_same_key_repeatedly_no_size_growth(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        for i in range(100):
            cache.set("k", i)
        assert len(cache) == 1
        assert cache.get("k") == 99  # last value

    def test_zero_ttl_entry_expires_immediately(self):
        cache: LRUCache[str, str] = LRUCache(capacity=5)
        # A ttl=0 means expires_at = now + 0 = now, which is immediately expired
        # Allow a tiny sleep to ensure time.monotonic() >= expires_at
        cache.set("k", "v", ttl=0.0001)
        time.sleep(0.01)
        assert cache.get("k") is None

    def test_new_key_with_expired_ttl_does_not_evict_valid_entry(self):
        """Dead-on-arrival new entries must not evict valid LRU items."""
        cache: LRUCache[str, int] = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        # Cache is full; inserting a new key with ttl=0 should be a no-op.
        cache.set("c", 3, ttl=0)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") is None
        assert len(cache) == 2

    def test_new_key_with_negative_ttl_does_not_evict_valid_entry(self):
        """Negative TTL on a new key into a full cache must not evict valid items."""
        cache: LRUCache[str, int] = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3, ttl=-5)
        assert cache.get("a") == 1
        assert cache.get("b") == 2
        assert cache.get("c") is None
        assert len(cache) == 2

    def test_update_existing_key_with_expired_ttl_still_updates(self):
        """Updating an *existing* key with a zero/negative TTL should still work
        (the key already occupies a slot; no eviction is needed)."""
        cache: LRUCache[str, int] = LRUCache(capacity=2)
        cache.set("a", 1)
        cache.set("b", 2)
        # Update existing key "a" with an immediately-expiring TTL.
        cache.set("a", 99, ttl=0.0001)
        time.sleep(0.01)
        assert cache.get("a") is None  # expired
        assert cache.get("b") == 2    # unaffected

    def test_delete_then_set_works(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        cache.delete("k")
        cache.set("k", 2)
        assert cache.get("k") == 2

    def test_clear_then_set_works(self):
        cache: LRUCache[str, int] = LRUCache(capacity=5)
        cache.set("k", 1)
        cache.clear()
        cache.set("k", 2)
        assert cache.get("k") == 2
        assert len(cache) == 1
