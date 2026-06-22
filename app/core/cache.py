import os
import time
from typing import Any

import json

from app.core.log import get_logger

logger = get_logger(__name__)

_redis = None
_redis_available = False


def _get_redis():
    global _redis, _redis_available
    if _redis is None and not _redis_available:
        import redis as redis_module
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            _redis = redis_module.from_url(redis_url, socket_timeout=2.0, decode_responses=True)
            _redis.ping()
            _redis_available = True
            logger.info("Redis connected at %s", redis_url)
        except Exception as e:
            _redis_available = False
            logger.warning("Redis unavailable, falling back to in-memory cache: %s", e)
    return _redis if _redis_available else None


class MemoryCache:
    def __init__(self):
        self._data: dict[str, tuple[Any, float, int]] = {}
        self._default_ttl = 300

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry:
            value, store_time, ttl = entry
            if time.time() - store_time < ttl:
                return value
            del self._data[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        self._data[key] = (value, time.time(), ttl or self._default_ttl)
        if len(self._data) > 1000:
            self._evict()

    def delete(self, key: str):
        self._data.pop(key, None)

    def _evict(self):
        now = time.time()
        self._data = {k: v for k, v in self._data.items() if now - v[1] < v[2]}

    def clear(self):
        self._data.clear()


_memory_cache = MemoryCache()


class CacheService:
    def __init__(self, default_ttl: int = 300):
        self._default_ttl = default_ttl
        self._redis = _get_redis()

    def get(self, key: str) -> Any | None:
        if self._redis:
            try:
                val = self._redis.get(key)
                if val is not None:
                    try:
                        return json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        return val
            except Exception:
                logger.exception("Redis get failed for key: %s", key)
        return _memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None):
        ttl = ttl or self._default_ttl
        payload = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        if self._redis:
            try:
                self._redis.setex(key, ttl, payload)
                return
            except Exception:
                logger.exception("Redis set failed for key: %s", key)
        _memory_cache.set(key, value, ttl)

    def delete(self, key: str):
        if self._redis:
            try:
                self._redis.delete(key)
                return
            except Exception:
                logger.exception("Redis delete failed for key: %s", key)
        _memory_cache.delete(key)

    def clear(self):
        if self._redis:
            try:
                self._redis.flushdb()
            except Exception:
                logger.exception("Redis flushdb failed")
        _memory_cache.clear()


_cache_service: CacheService | None = None


def get_cache() -> CacheService:
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service
