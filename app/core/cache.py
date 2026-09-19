"""In-memory and Redis-backed caching with automatic fallback.

Write-through: ``set``/``delete`` always touch BOTH Redis and the
in-memory fallback so the two layers never diverge when Redis blips.
``LOG_LEVEL`` is honoured via :mod:`app.core.log`; the default TTL falls
back to ``settings.CACHE_DEFAULT_TTL`` when no explicit TTL is given.
"""

import asyncio
import json
import random
import threading
import time
from functools import partial
from typing import Any
from urllib.parse import urlparse, urlunparse

from app.core.log import get_logger

logger = get_logger(__name__)

_redis = None
_redis_available = False
_redis_lock = threading.Lock()
_redis_last_attempt = 0.0
_REDIS_RETRY_INTERVAL = 30.0


def _redact_redis_url(url: str) -> str:
    """Redact any password in a Redis URL before logging."""
    try:
        parts = urlparse(url)
        if parts.password:
            netloc = parts.hostname or ""
            if parts.port:
                netloc += f":{parts.port}"
            # Keep username (usually empty) but drop password.
            if parts.username:
                netloc = f"{parts.username}:***@{netloc}"
            return urlunparse(parts._replace(netloc=netloc))
    except Exception:
        pass
    # Fallback: mask :password@ pattern.
    import re as _re

    return _re.sub(r"://([^:/@]+):[^@]+@", r"://\1:***@", url)


def _mark_redis_unavailable(reason: Exception | None = None) -> None:
    """Reset Redis availability flag and connection handle on failure."""
    global _redis, _redis_available
    _redis = None
    _redis_available = False
    if reason:
        logger.warning("Redis operation failed, falling back to in-memory cache: %s", reason)


def _get_redis():
    global _redis, _redis_available, _redis_last_attempt
    now = time.time()
    if _redis is not None and _redis_available:
        return _redis
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
            client = redis_module.from_url(redis_url, socket_timeout=2.0, decode_responses=True)
            client.ping()
            _redis = client
            _redis_available = True
            logger.info("Redis connected at %s", _redact_redis_url(redis_url))
        except Exception as e:
            _redis = None
            _redis_available = False
            logger.warning("Redis unavailable, falling back to in-memory cache: %s", e)
    return _redis if _redis_available else None


_MISSING: Any = object()

_MISSING_SENTINEL = _MISSING


def _jittered_ttl(base: int, spread: int = 60) -> int:
    """Add ±``spread`` jitter to TTL to avoid thundering-herd expiry.

    Crypto callers (predict/trend, default 300s) stampede when keys expire in
    lockstep; jitter spreads recompute load. Spread scales down for small TTLs
    so a 60s TTL never collapses to ~1s. Always returns >= 1.
    """
    try:
        b = int(base)
        s = max(1, min(int(spread), b // 3))
        return max(1, b + random.randint(-s, s))
    except Exception:
        return int(base)


class MemoryCache:
    def __init__(self):
        self._data: dict[str, tuple[Any, float, int]] = {}
        self._default_ttl = 300
        self._lock = threading.Lock()

    def get(self, key: str, default: Any | None = None) -> Any | None:
        """Return ``default`` on miss/expiry so callers can distinguish ``None`` values."""
        with self._lock:
            entry = self._data.get(key)
            if entry:
                value, store_time, ttl = entry
                if time.time() - store_time < ttl:
                    return value
                del self._data[key]
        return default

    def set(self, key: str, value: Any, ttl: int | None = None):
        with self._lock:
            self._data[key] = (value, time.time(), ttl if ttl is not None else self._default_ttl)
            if len(self._data) > 1000:
                self._evict()

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)

    def _evict(self):
        # Called while self._lock is already held
        now = time.time()
        self._data = {k: v for k, v in self._data.items() if now - v[1] < v[2]}
        # Bound memory: if still over capacity after expiring TTLs,
        # evict oldest (FIFO/LRU by store_time) down to 1000 entries.
        if len(self._data) > 1000:
            excess = len(self._data) - 1000
            oldest = sorted(self._data.items(), key=lambda kv: kv[1][1])[:excess]
            for k, _ in oldest:
                self._data.pop(k, None)

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
            try:
                return bytes.fromhex(raw[6:])
            except (ValueError, TypeError):
                return payload
        return raw
    try:
        return json.loads(payload)
    except (ValueError, TypeError):
        # ValueError covers JSONDecodeError + binascii errors.
        return payload


class CacheService:
    def __init__(self, default_ttl: int | None = None):
        if default_ttl is None:
            try:
                from app.core.config import settings  # noqa: PLC0415

                default_ttl = int(settings.CACHE_DEFAULT_TTL)
            except Exception:
                default_ttl = 300
        self._default_ttl = default_ttl
        # NOTE: Redis is resolved per-operation via _get_redis() (not
        # snapshotted here) so reconnects are picked up automatically.

    def get(self, key: str, default: Any | None = None) -> Any | None:
        redis = _get_redis()
        if redis:
            try:
                val = redis.get(key)
                if val is not None:
                    return _unwrap_stored(val)
                # Authoritative miss in Redis: return default, do not resurrect stale local memory
                return default
            except Exception as exc:
                logger.exception("Redis get failed for key: %s", key)
                _mark_redis_unavailable(exc)
        return _memory_cache.get(key, default)

    def set(self, key: str, value: Any, ttl: int | None = None):
        base = ttl if ttl is not None else self._default_ttl
        # ROUND-2: jitter TTL so bulk keys (e.g. crypto predict/trend 300s)
        # don't expire simultaneously and stampede origin.
        ttl = _jittered_ttl(base)
        payload = _wrap_for_storage(value)
        # Write-through: always update memory so fallback stays coherent,
        # even when Redis is available.
        _memory_cache.set(key, value, ttl)
        redis = _get_redis()
        if redis:
            try:
                redis.setex(key, ttl, payload)
            except Exception as exc:
                logger.exception("Redis set failed for key: %s", key)
                _mark_redis_unavailable(exc)

    def delete(self, key: str):
        # Delete-through: remove from BOTH layers to avoid stale reads.
        _memory_cache.delete(key)
        redis = _get_redis()
        if redis:
            try:
                redis.delete(key)
            except Exception as exc:
                logger.exception("Redis delete failed for key: %s", key)
                _mark_redis_unavailable(exc)

    def clear(self):
        _memory_cache.clear()
        # Best-effort: reset in-process singleflight/cached layers too.
        try:
            from app.api.routes.tools_fng import _FNG_LOCKS  # noqa: PLC0415
            from app.api.routes.tools_fng import _get_cached_fng  # noqa: PLC0415

            _FNG_LOCKS.clear()
            if hasattr(_get_cached_fng, "_cache"):
                _get_cached_fng._cache.clear()  # type: ignore[attr-defined]
        except Exception:
            pass
        redis = _get_redis()
        if redis:
            try:
                # ROUND-2: never flushdb() — it nukes unrelated DBs/tenants.
                # Delete only our own namespaces via scan_iter.
                for pattern in ("cache:*", "ratelimit:*", "predict:*", "trend:*", "fng:*", "seo:*", "blog:*"):
                    try:
                        for key in redis.scan_iter(match=pattern, count=500):
                            try:
                                redis.delete(key)
                            except Exception:
                                logger.exception("Redis delete failed for key: %s", key)
                    except Exception:
                        logger.exception("Redis scan_iter failed for pattern: %s", pattern)
            except Exception as exc:
                logger.exception("Redis clear failed")
                _mark_redis_unavailable(exc)

    # ROUND-2: async wrappers — redis-py is blocking, so offload to a worker
    # thread when called from async code. Sync get/set/delete above are kept
    # for sync callers.
    async def async_get(self, key: str, default: Any | None = None) -> Any | None:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self.get, key, default))

    async def async_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, partial(self.set, key, value, ttl))

    async def async_delete(self, key: str) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, partial(self.delete, key))


_cache_service: CacheService | None = None
_cache_service_lock = threading.Lock()


def get_cache() -> CacheService:
    global _cache_service
    if _cache_service is None:
        with _cache_service_lock:
            if _cache_service is None:  # double-checked locking
                _cache_service = CacheService()
    return _cache_service
