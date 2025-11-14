"""
Advanced Caching System
Multi-layer caching with Redis, in-memory, and database-level optimizations.
"""

import asyncio
import json
import pickle
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)


class CacheKey:
    """Smart cache key generator with namespacing and versioning"""

    def __init__(self, namespace: str = "soleflip"):
        self.namespace = namespace

    def generate(self, *parts, version: str = "v1") -> str:
        """Generate cache key from parts"""
        key_parts = [self.namespace, version] + [str(part) for part in parts]
        return ":".join(key_parts)

    def pattern(self, pattern: str) -> str:
        """Generate cache pattern for bulk operations"""
        return f"{self.namespace}:*:{pattern}:*"


class InMemoryCache:
    """High-performance in-memory cache with TTL and size limits"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key not in self.cache:
                return None

            entry = self.cache[key]

            # Check if expired
            if entry["expires_at"] < time.time():
                del self.cache[key]
                self.access_times.pop(key, None)
                return None

            # Update access time
            self.access_times[key] = time.time()

            logger.debug("In-memory cache hit", key=key)
            return entry["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache"""
        async with self._lock:
            # Evict if cache is full
            if len(self.cache) >= self.max_size:
                await self._evict_lru()

            ttl = ttl or self.default_ttl
            expires_at = time.time() + ttl

            self.cache[key] = {"value": value, "expires_at": expires_at, "created_at": time.time()}
            self.access_times[key] = time.time()

            logger.debug("In-memory cache set", key=key, ttl=ttl)

    async def delete(self, key: str) -> bool:
        """Delete value from cache"""
        async with self._lock:
            if key in self.cache:
                del self.cache[key]
                self.access_times.pop(key, None)
                logger.debug("In-memory cache delete", key=key)
                return True
            return False

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self.cache.clear()
            self.access_times.clear()
            logger.info("In-memory cache cleared")

    async def _evict_lru(self) -> None:
        """Evict least recently used entries"""
        if not self.access_times:
            return

        # Find the least recently used key
        lru_key = min(self.access_times.keys(), key=lambda k: self.access_times[k])

        del self.cache[lru_key]
        del self.access_times[lru_key]

        logger.debug("Evicted LRU entry", key=lru_key)

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        now = time.time()
        expired_count = sum(1 for entry in self.cache.values() if entry["expires_at"] < now)

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "expired_entries": expired_count,
            "hit_rate": getattr(self, "_hit_rate", 0.0),
        }


class RedisCache:
    """Redis-based distributed cache"""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.redis_url = redis_url
        self.connected = False

    async def connect(self):
        """Connect to Redis"""
        try:
            import redis.asyncio as redis

            if self.redis_url:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

            # Test connection
            await self.redis_client.ping()
            self.connected = True

            logger.info("Redis cache connected")

        except ImportError:
            logger.warning("Redis not available, using in-memory cache only")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache"""
        if not self.connected:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                # Try to deserialize JSON first, then pickle
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return pickle.loads(value.encode("latin1"))
            return None

        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis cache"""
        if not self.connected:
            return False

        try:
            # Try to serialize as JSON first, then pickle
            try:
                serialized_value = json.dumps(value, default=str)
            except (TypeError, ValueError):
                serialized_value = pickle.dumps(value).decode("latin1")

            if ttl:
                await self.redis_client.setex(key, ttl, serialized_value)
            else:
                await self.redis_client.set(key, serialized_value)

            return True

        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from Redis cache"""
        if not self.connected:
            return False

        try:
            result = await self.redis_client.delete(key)
            return result > 0

        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if not self.connected:
            return 0

        try:
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                return await self.redis_client.delete(*keys)
            return 0

        except Exception as e:
            logger.warning(f"Redis clear pattern error: {e}")
            return 0


class MultiLevelCache:
    """Multi-level cache with L1 (in-memory) and L2 (Redis) layers"""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        l1_max_size: int = 1000,
        l1_ttl: int = 300,  # 5 minutes
        l2_ttl: int = 3600,  # 1 hour
    ):
        self.key_generator = CacheKey()
        self.l1_cache = InMemoryCache(max_size=l1_max_size, default_ttl=l1_ttl)
        self.l2_cache = RedisCache(redis_url)
        self.l2_ttl = l2_ttl

        # Performance tracking
        self.stats = {"l1_hits": 0, "l2_hits": 0, "misses": 0, "sets": 0}

    async def initialize(self):
        """Initialize cache layers"""
        await self.l2_cache.connect()
        logger.info("Multi-level cache initialized")

    async def get(self, key: str) -> Optional[Any]:
        """Get value with L1 -> L2 fallback"""

        # Try L1 cache first
        value = await self.l1_cache.get(key)
        if value is not None:
            self.stats["l1_hits"] += 1
            return value

        # Try L2 cache
        value = await self.l2_cache.get(key)
        if value is not None:
            self.stats["l2_hits"] += 1
            # Populate L1 cache
            await self.l1_cache.set(key, value)
            return value

        self.stats["misses"] += 1
        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in both cache layers"""

        # Set in L1 cache
        l1_ttl = min(ttl or self.l1_cache.default_ttl, self.l1_cache.default_ttl)
        await self.l1_cache.set(key, value, l1_ttl)

        # Set in L2 cache
        l2_ttl = ttl or self.l2_ttl
        await self.l2_cache.set(key, value, l2_ttl)

        self.stats["sets"] += 1

    async def delete(self, key: str) -> bool:
        """Delete from both cache layers"""
        l1_deleted = await self.l1_cache.delete(key)
        l2_deleted = await self.l2_cache.delete(key)
        return l1_deleted or l2_deleted

    async def clear_pattern(self, pattern: str) -> int:
        """Clear entries matching pattern from both layers"""
        # L1 cache doesn't support patterns, so clear all
        await self.l1_cache.clear()

        # Clear pattern from L2
        return await self.l2_cache.clear_pattern(pattern)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats["l1_hits"] + self.stats["l2_hits"] + self.stats["misses"]

        if total_requests == 0:
            return {**self.stats, "hit_rate": 0.0, "l1_hit_rate": 0.0}

        hit_rate = (self.stats["l1_hits"] + self.stats["l2_hits"]) / total_requests
        l1_hit_rate = self.stats["l1_hits"] / total_requests

        return {
            **self.stats,
            "hit_rate": hit_rate,
            "l1_hit_rate": l1_hit_rate,
            "total_requests": total_requests,
        }


# Decorators for caching
def cache_result(
    ttl: int = 3600,
    key_prefix: Optional[str] = None,
    cache_instance: Optional[MultiLevelCache] = None,
):
    """Decorator to cache function results"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Use global cache if not provided
            cache = cache_instance or get_cache()

            # Generate cache key
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            key = cache.key_generator.generate(prefix, *args, str(sorted(kwargs.items())))

            # Try to get from cache
            cached_result = await cache.get(key)
            if cached_result is not None:
                logger.debug("Cache hit", function=func.__name__, key=key)
                return cached_result

            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache.set(key, result, ttl)

            logger.debug("Cache miss, result cached", function=func.__name__, key=key)
            return result

        return wrapper

    return decorator


def invalidate_cache(pattern: str, cache_instance: Optional[MultiLevelCache] = None):
    """Decorator to invalidate cache patterns after function execution"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)

            # Invalidate cache pattern
            cache = cache_instance or get_cache()
            cleared = await cache.clear_pattern(pattern)

            if cleared > 0:
                logger.info(f"Invalidated {cleared} cache entries", pattern=pattern)

            return result

        return wrapper

    return decorator


# Global cache instance
_cache: Optional[MultiLevelCache] = None


async def initialize_cache(redis_url: Optional[str] = None):
    """Initialize the global cache"""
    global _cache
    _cache = MultiLevelCache(redis_url=redis_url)
    await _cache.initialize()


def get_cache() -> MultiLevelCache:
    """Get the global cache instance"""
    global _cache
    if _cache is None:
        raise RuntimeError("Cache not initialized. Call initialize_cache() first.")
    return _cache


# Specific cache implementations for common use cases
class ProductCache:
    """Specialized cache for product data"""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache

    async def get_product(self, product_id: UUID) -> Optional[Dict]:
        """Get cached product data"""
        key = self.cache.key_generator.generate("product", str(product_id))
        return await self.cache.get(key)

    async def set_product(self, product_id: UUID, product_data: Dict, ttl: int = 1800):
        """Cache product data"""
        key = self.cache.key_generator.generate("product", str(product_id))
        await self.cache.set(key, product_data, ttl)

    async def invalidate_product(self, product_id: UUID):
        """Invalidate product cache"""
        key = self.cache.key_generator.generate("product", str(product_id))
        await self.cache.delete(key)

    async def invalidate_brand_products(self, brand_id: UUID):
        """Invalidate all products for a brand"""
        pattern = self.cache.key_generator.pattern(f"product:*:brand:{brand_id}")
        return await self.cache.clear_pattern(pattern)


class ImportCache:
    """Specialized cache for import batch data"""

    def __init__(self, cache: MultiLevelCache):
        self.cache = cache

    async def get_batch_status(self, batch_id: UUID) -> Optional[Dict]:
        """Get cached import batch status"""
        key = self.cache.key_generator.generate("import_batch", str(batch_id))
        return await self.cache.get(key)

    async def set_batch_status(self, batch_id: UUID, status_data: Dict, ttl: int = 300):
        """Cache import batch status"""
        key = self.cache.key_generator.generate("import_batch", str(batch_id))
        await self.cache.set(key, status_data, ttl)

    async def invalidate_batch(self, batch_id: UUID):
        """Invalidate batch cache"""
        key = self.cache.key_generator.generate("import_batch", str(batch_id))
        await self.cache.delete(key)


def get_product_cache() -> ProductCache:
    """Get product cache instance"""
    return ProductCache(get_cache())


def get_import_cache() -> ImportCache:
    """Get import cache instance"""
    return ImportCache(get_cache())
