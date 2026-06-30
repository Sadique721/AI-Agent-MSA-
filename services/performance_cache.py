"""
services/performance_cache.py
=============================
Performance Cache Service.
Implements thread-safe LRU caches for embeddings, query expansions/rewrites,
search results, and LLM responses to optimize latencies.
"""

import logging
import threading
from collections import OrderedDict
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger("msa.services.cache")


class LRUCache:
    """
    Thread-safe Least Recently Used (LRU) Cache with hit/miss telemetry tracking.
    """
    def __init__(self, max_size: int = 500):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def get(self, key: Any) -> Optional[Any]:
        """Retrieves an item from cache, moving it to the end (most recently used)."""
        with self._lock:
            if key in self.cache:
                self.hits += 1
                self.cache.move_to_end(key)
                return self.cache[key]
            self.misses += 1
            return None

    def put(self, key: Any, value: Any) -> None:
        """Puts an item in cache, evicting the oldest if capacity is exceeded."""
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    def clear(self) -> None:
        """Clears the cache and resets stats."""
        with self._lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0

    @property
    def hit_ratio(self) -> float:
        """Returns the cache hit ratio."""
        total = self.hits + self.misses
        return round(self.hits / total, 4) if total > 0 else 0.0


class RAGPerformanceCache:
    """
    Central manager hosting dedicated caches for embeddings, searches, rewrites, and responses.
    """
    def __init__(self):
        self.embeddings = LRUCache(max_size=2000)
        self.searches = LRUCache(max_size=500)
        self.rewrites = LRUCache(max_size=500)
        self.responses = LRUCache(max_size=500)

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Compiles hits, misses, sizes, and hit ratios for all caches."""
        stats = {}
        for name, cache in [
            ("embeddings", self.embeddings),
            ("searches", self.searches),
            ("rewrites", self.rewrites),
            ("responses", self.responses)
        ]:
            stats[name] = {
                "size": len(cache.cache),
                "max_size": cache.max_size,
                "hits": cache.hits,
                "misses": cache.misses,
                "hit_ratio": cache.hit_ratio
            }
        return stats

    def clear_all(self) -> None:
        """Flushes all caches."""
        self.embeddings.clear()
        self.searches.clear()
        self.rewrites.clear()
        self.responses.clear()
        logger.info("RAG Cache: flushed all caches.")
