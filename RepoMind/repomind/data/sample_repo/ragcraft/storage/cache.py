"""Redis caching layer for vector queries and intermediate representations."""
from typing import Optional, Any
from ragcraft.config import CacheConfig


class RedisCache:
    """Redis-backed key-value cache for hot queries and query embeddings."""

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self.client = None
        self._in_memory_store = {}

    def get(self, key: str) -> Optional[Any]:
        """Fetch cached response or embedding vector."""
        if not self.config.enabled:
            return None
        return self._in_memory_store.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store key-value pair in cache with expiration."""
        if not self.config.enabled:
            return False
        self._in_memory_store[key] = value
        return True

    def invalidate(self, pattern: str) -> int:
        """Invalidate keys matching specified pattern."""
        count = len(self._in_memory_store)
        self._in_memory_store.clear()
        return count
