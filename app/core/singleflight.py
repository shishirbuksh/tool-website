"""Singleflight helpers: per-key asyncio locks and semaphores.

Deduplicates concurrent async work (cache stampedes) by sharing one
``asyncio.Lock`` / ``asyncio.Semaphore`` per key. Primitives are bound to
the running event loop, so entries are keyed by ``(loop_id, key)`` and
recreated when the loop changes (tests, worker reloads). Call sites are
NOT refactored here — import ``get_lock`` / ``get_semaphore`` in new code.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Hashable

__all__ = ["get_lock", "get_semaphore", "clear"]

_LOCKS: dict[tuple[int, Hashable], asyncio.Lock] = {}
_SEMAPHORES: dict[tuple[int, Hashable], asyncio.Semaphore] = {}
_GUARD = threading.Lock()
_MAX_ENTRIES = 64


def get_lock(key: Hashable) -> asyncio.Lock:
    """Return the shared ``asyncio.Lock`` for ``key`` on this loop."""
    loop_id = id(asyncio.get_running_loop())
    cache_key = (loop_id, key)
    with _GUARD:
        lock = _LOCKS.get(cache_key)
        if lock is None:
            lock = asyncio.Lock()
            _LOCKS[cache_key] = lock
            if len(_LOCKS) > _MAX_ENTRIES:
                _LOCKS.pop(next(iter(_LOCKS)), None)
        return lock


def get_semaphore(key: Hashable, permits: int = 1) -> asyncio.Semaphore:
    """Return the shared ``asyncio.Semaphore`` for ``key`` on this loop."""
    if permits < 1:
        raise ValueError("permits must be >= 1")
    loop_id = id(asyncio.get_running_loop())
    cache_key = (loop_id, key)
    with _GUARD:
        sem = _SEMAPHORES.get(cache_key)
        if sem is None:
            sem = asyncio.Semaphore(permits)
            _SEMAPHORES[cache_key] = sem
            if len(_SEMAPHORES) > _MAX_ENTRIES:
                _SEMAPHORES.pop(next(iter(_SEMAPHORES)), None)
        return sem


def clear() -> None:
    """Drop all cached locks/semaphores (tests, cache clear)."""
    with _GUARD:
        _LOCKS.clear()
        _SEMAPHORES.clear()
