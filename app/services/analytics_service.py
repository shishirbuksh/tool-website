"""Page-view analytics service: SQLite-backed, thread-safe, with configurable retention."""

import asyncio
import os
import queue
import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta
from functools import partial

from app.core.config import settings
from app.core.log import get_logger

logger = get_logger(__name__)

DATA_DIR = os.path.join(settings.base_dir, "var", "data")
DB_PATH = os.path.join(DATA_DIR, "analytics.db")

_RETENTION_DAYS = settings.ANALYTICS_RETENTION_DAYS
_CLEANUP_INTERVAL = settings.ANALYTICS_CLEANUP_INTERVAL
_last_cleanup = 0.0
_cleanup_lock = threading.Lock()
_write_lock = threading.RLock()
_POOL_SIZE = 5

_conn_pool: queue.Queue | None = None
_pool_lock = threading.Lock()


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _init_pool():
    global _conn_pool
    _ensure_dir()
    pool = queue.Queue(maxsize=_POOL_SIZE)
    for _ in range(_POOL_SIZE):
        conn = sqlite3.connect(DB_PATH, timeout=5.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  name TEXT NOT NULL,"
            "  category TEXT NOT NULL DEFAULT 'page_view',"
            "  ts TEXT NOT NULL"
            ")"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_name ON events(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_category_ts ON events(category, ts)")
        conn.commit()
        pool.put(conn)
    _conn_pool = pool


def _get_conn() -> sqlite3.Connection:
    global _conn_pool, _pool_lock
    with _pool_lock:
        if _conn_pool is None:
            _init_pool()
    try:
        return _conn_pool.get(timeout=10)
    except queue.Empty:
        raise RuntimeError("Analytics connection pool exhausted — all 5 connections in use") from None


def _put_conn(conn: sqlite3.Connection):
    _conn_pool.put(conn)


def track(name: str, category: str = "page_view"):
    global _last_cleanup
    now = time.time()
    with _write_lock:
        conn = None
        try:
            conn = _get_conn()
            conn.execute(
                "INSERT INTO events (name, category, ts) VALUES (?, ?, ?)",
                (name, category, datetime.now(UTC).isoformat()),
            )
            conn.commit()
        except Exception:
            logger.exception("Failed to track analytics event")
        finally:
            if conn:
                _put_conn(conn)

    if now - _last_cleanup > _CLEANUP_INTERVAL:
        with _cleanup_lock:
            if now - _last_cleanup > _CLEANUP_INTERVAL:
                _last_cleanup = now
                _cleanup_old_events()


def get_counts(limit: int = 50) -> dict:
    conn = None
    try:
        conn = _get_conn()
        cutoff = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS)).isoformat()
        cursor = conn.execute(
            "SELECT name, COUNT(*) as cnt FROM events WHERE ts >= ? GROUP BY name ORDER BY cnt DESC LIMIT ?",
            (cutoff, limit),
        )
        return dict(cursor.fetchall())
    except Exception:
        logger.exception("Failed to get analytics counts")
        return {}
    finally:
        if conn:
            _put_conn(conn)


def _cleanup_old_events():
    with _write_lock:
        conn = None
        try:
            cutoff = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS)).isoformat()
            conn = _get_conn()
            conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            conn.commit()
        except Exception:
            logger.exception("Failed to cleanup old analytics events")
        finally:
            if conn:
                _put_conn(conn)


async def async_track(name: str, category: str = "page_view"):
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, partial(track, name, category))


async def async_get_counts(limit: int = 50) -> dict:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(get_counts, limit))
