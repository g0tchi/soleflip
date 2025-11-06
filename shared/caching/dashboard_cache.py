"""
Dashboard metrics caching system
High-performance in-memory cache with TTL for dashboard data
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class DashboardCache:
    """In-memory cache for dashboard metrics with TTL"""

    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data if not expired"""
        async with self._lock:
            if key not in self._cache:
                return None

            cache_entry = self._cache[key]
            expires_at = cache_entry.get("expires_at")

            if expires_at and datetime.utcnow() > expires_at:
                # Cache expired, remove it
                del self._cache[key]
                logger.debug("Cache expired and removed", key=key)
                return None

            logger.debug("Cache hit", key=key)
            return cache_entry.get("data")

    async def set(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> None:
        """Set cache data with TTL"""
        async with self._lock:
            ttl = ttl or self._default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)

            self._cache[key] = {
                "data": data,
                "expires_at": expires_at,
                "cached_at": datetime.utcnow(),
            }

            logger.debug("Data cached", key=key, ttl=ttl)

    async def invalidate(self, key: str) -> bool:
        """Manually invalidate cache entry"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug("Cache invalidated", key=key)
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info("Cache cleared", entries_removed=count)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_entries = len(self._cache)
        expired_entries = 0
        now = datetime.utcnow()

        for entry in self._cache.values():
            expires_at = entry.get("expires_at")
            if expires_at and now > expires_at:
                expired_entries += 1

        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "active_entries": total_entries - expired_entries,
            "cache_size_bytes": len(json.dumps(list(self._cache.keys()), default=str)),
        }


# Global cache instance
_dashboard_cache = DashboardCache()


def get_dashboard_cache() -> DashboardCache:
    """Get the global dashboard cache instance"""
    return _dashboard_cache
