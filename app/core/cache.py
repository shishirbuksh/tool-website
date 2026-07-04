"""In-memory and Redis-backed caching with automatic fallback."""

import json
import threading
import time
from typing import Any

from app.core.log import get_logger

logger = get_logger(__name__)

_redis = None
_redis_available = False
_redis_lock = threading.Lock()
_redis_last_attempt = 0.0
_REDIS_RETRY_INTERVAL = 30.0


def _get_redis():
    global _redis, _redis_available, _redis_last_attempt
    now = time.time()
    if _redis is not None and _redis_available:
        try:
            _redis.ping()
            return _redis
        except Exception:
            _redis = None
            _redis_available = False
            logger.warning("Redis connection lost, will retry")
    if now - _redis_last_attempt < _REDIS_RETRY_INTERVAL:
        return None
    with _redis_lock:
        if now - _redis_last_attempt < _REDIS_RETRY_INTERVAL:
            return None
        _redis_last_attempt = now
        try:
            import redis as redis_module

            from app.core.config import settings
            redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
            _redis = redis_module.from_url(redis_url, socket_timeout=2.0, decode_responses=True)
            _redis.ping()
            _redis_available = True
            logger.info("Redis connected at %s", redis_url)
        except Exception as e:
            _redis = None
            _redis_available = False
            logger.warning("Redis unavailable, falling back to in-memory cache: %s", e)
    return _redis if _redis_available else None


class MemoryCache:
    def __init__(self):
        self._data: dict[str, tuple[Any, float, int]] = {}
        self._default_ttl = 300
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._data.get(key)
            if entry:
                value, store_time, ttl = entry
                if time.time() - store_time < ttl:
                    return value
                del self._data[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None):
        with self._lock:
            self._data[key] = (value, time.time(), ttl or self._default_ttl)
            if len(self._data) > 1000:
                self._evict()

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)

    def _evict(self):
        # Called while self._lock is already held
        now = time.time()
        self._data = {k: v for k, v in self._data.items() if now - v[1] < v[2]}

    def clear(self):
        with self._lock:
            self._data.clear()


_memory_cache = MemoryCache()

_STR_MARKER = "\x00str\x00"


def _wrap_for_storage(value: Any) -> str:
    if isinstance(value, str):
        return _STR_MARKER + value
    if isinstance(value, bytes):
        return _STR_MARKER + "bytes:" + value.hex()
    try:
        return json.dumps(value, default=str)
    except (TypeError, ValueError):
        return json.dumps(str(value))


def _unwrap_stored(payload: str) -> Any:
    if payload.startswith(_STR_MARKER):
        raw = payload[len(_STR_MARKER):]
        if raw.startswith("bytes:"):
            return bytes.fromhex(raw[6:])
        return raw
    try:
        return json.loads(payload)
    except (json.JSONDecodeError, TypeError):
        return payload


class CacheService:
    def __init__(self, default_ttl: int = 300):
        self._default_ttl = default_ttl
        self._redis = _get_redis()

    def get(self, key: str) -> Any | None:
        if self._redis:
            try:
                val = self._redis.get(key)
                if val is not None:
                    return _unwrap_stored(val)
            except Exception:
                logger.exception("Redis get failed for key: %s", key)
        return _memory_cache.get(key)

    def set(self, key: str, value: Any, ttl: int | None = None):
        ttl = ttl or self._default_ttl
        payload = _wrap_for_storage(value)
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
_cache_service_lock = threading.Lock()


def get_cache() -> CacheService:
    global _cache_service
    if _cache_service is None:
        with _cache_service_lock:
            if _cache_service is None:  # double-checked locking
                _cache_service = CacheService()
    return _cache_service
