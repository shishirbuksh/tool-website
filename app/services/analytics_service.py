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


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _init_pool() -> None:
    global _conn_pool
    _ensure_dir()
    pool = queue.Queue(maxsize=_POOL_SIZE)
    for _ in range(_POOL_SIZE):
        conn = sqlite3.connect(DB_PATH, timeout=5.0, check_same_thread=False)
        # ROUND-2 scalability/durability: WAL + NORMAL sync for concurrent
        # readers/writers; busy_timeout avoids "database is locked" under
        # burst; wal_autocheckpoint bounds WAL file growth. 90d retention
        # is enforced by _cleanup_old_events (see _RETENTION_DAYS).
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute("PRAGMA wal_autocheckpoint=1000;")
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


def _put_conn(conn: sqlite3.Connection | None) -> None:
    if conn is None:
        return
    try:
        if _conn_pool is None:
            try:
                conn.close()
            except Exception:
                pass
            return
        _conn_pool.put_nowait(conn)
    except queue.Full:
        # Pool full (e.g. double-put); close extra to avoid leak, don't block.
        try:
            conn.close()
        except Exception:
            pass
        logger.warning("Analytics connection pool full — closed extra connection")
    except Exception:
        logger.exception("Failed to return analytics connection to pool")


def _sanitize_field(value: str, max_len: int) -> str:
    """Strip newlines/CRs and truncate to max_len for log/DB safety."""
    s = str(value or "")
    s = s.replace("\r", " ").replace("\n", " ").strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s


def track(name: str, category: str = "page_view") -> bool:
    global _last_cleanup
    # Validate/truncate early to bound DB + log size.
    name = _sanitize_field(name, 200)
    if not name:
        return False
    category = _sanitize_field(category, 50) or "page_view"
    now = time.monotonic()
    # Get connection BEFORE acquiring _write_lock so pool timeout
    # (10s) doesn't hold the write lock and stall other writers.
    try:
        conn = _get_conn()
    except RuntimeError:
        logger.error("Failed to track analytics event: connection pool exhausted")
        return False
    except Exception:
        logger.exception("Failed to track analytics event")
        return False
    try:
        with _write_lock:
            try:
                conn.execute(
                    "INSERT INTO events (name, category, ts) VALUES (?, ?, ?)",
                    (name, category, datetime.now(UTC).isoformat()),
                )
                conn.commit()
            except Exception:
                logger.exception("Failed to track analytics event")
                return False
    finally:
        _put_conn(conn)

    if now - _last_cleanup > _CLEANUP_INTERVAL:
        with _cleanup_lock:
            if now - _last_cleanup > _CLEANUP_INTERVAL:
                _last_cleanup = now
                _cleanup_old_events()
    return True


def get_counts(limit: int = 50) -> dict[str, int]:
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


def _cleanup_old_events() -> None:
    # Get connection before write lock (see track()).
    try:
        conn = _get_conn()
    except RuntimeError:
        logger.error("Failed to cleanup old analytics events: pool exhausted")
        return
    except Exception:
        logger.exception("Failed to cleanup old analytics events")
        return
    try:
        with _write_lock:
            try:
                cutoff = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS)).isoformat()
                conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                conn.commit()
            except Exception:
                logger.exception("Failed to cleanup old analytics events")
    finally:
        _put_conn(conn)


async def async_track(name: str, category: str = "page_view") -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(track, name, category))


async def async_get_counts(limit: int = 50) -> dict[str, int]:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(get_counts, limit))
