```python
"""
LRU (Least Recently Used) Cache implementation using an OrderedDict.

Thread-safety: This implementation is NOT thread-safe. Do not access an
LRUCache instance concurrently from multiple threads without external locking.
"""

from collections import OrderedDict
from typing import Generic, TypeVar

KT = TypeVar("KT")
VT = TypeVar("VT")


class LRUCache(Generic[KT, VT]):
    """
    A fixed-capacity LRU cache.

    Items are evicted in least-recently-used order when the cache is full.
    Both get and put count as a 'use' and move the item to the most-recently-used
    position (end of the internal OrderedDict).

    Thread-safety: NOT thread-safe. External locking is required for concurrent use.
    """

    def __init__(self, capacity: int) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise TypeError(f"Capacity must be an int, got {type(capacity).__name__}")
        if capacity <= 0:
            raise ValueError(f"Capacity must be a positive integer, got {capacity}")
        self.capacity = capacity
        # OrderedDict preserves insertion order; move_to_end tracks recency.
        # Least-recently used is at the front (last=False); most-recently used at the end.
        self._cache: OrderedDict[KT, VT] = OrderedDict()

    def get(self, key: KT) -> VT:
        """
        Return the cached value for *key*.

        Raises KeyError if *key* is not present, consistent with standard
        Python mapping behaviour and avoiding ambiguity when -1 is a valid value.
        Accessing an existing key marks it as most-recently used.
        """
        try:
            value = self._cache[key]
        except KeyError:
            raise KeyError(key)
        self._cache.move_to_end(key)
        return value

    def put(self, key: KT, value: VT) -> None:
        """
        Insert or update *key* with *value*.

        If the cache is at capacity, the least-recently-used entry is evicted first.
        """
        if key in self._cache:
            self._cache.move_to_end(key)
            self._cache[key] = value
            return

        if len(self._cache) >= self.capacity:
            # popitem(last=False) removes the first (least-recently used) item.
            self._cache.popitem(last=False)

        self._cache[key] = value

    def __len__(self) -> int:
        return len(self._cache)

    def __repr__(self) -> str:
        return f"LRUCache(capacity={self.capacity}, size={len(self)})"


if __name__ == "__main__":
    cache: LRUCache[str, int] = LRUCache(capacity=3)

    cache.put("a", 1)
    cache.put("b", 2)
    cache.put("c", 3)

    assert cache.get("a") == 1  # 'a' is now MRU

    # 'b' is now LRU; adding 'd' should evict 'b'.
    cache.put("d", 4)
    try:
        cache.get("b")
        assert False, "Expected KeyError for evicted key"
    except KeyError:
        pass

    # Cache should now contain 'c', 'a', 'd'.
    assert cache.get("c") == 3
    assert cache.get("a") == 1
    assert cache.get("d") == 4

    # Update an existing key.
    cache.put("a", 99)
    assert cache.get("a") == 99
    assert len(cache) == 3

    # Error handling — invalid capacity.
    try:
        LRUCache(capacity=0)
        assert False, "Expected ValueError"
    except ValueError:
        pass

    try:
        LRUCache(capacity=True)  # type: ignore[arg-type]
        assert False, "Expected TypeError"
    except TypeError:
        pass

    try:
        LRUCache(capacity="3")  # type: ignore[arg-type]
        assert False, "Expected TypeError"
    except TypeError:
        pass

    print("All assertions passed.")
    print(cache)
```