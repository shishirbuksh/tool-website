import logging
import os
import queue
import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(settings.base_dir, "var", "data")
DB_PATH = os.path.join(DATA_DIR, "analytics.db")

_RETENTION_DAYS = 90
_BATCH_INTERVAL = 60
_last_cleanup = 0.0
_POOL_SIZE = 5

_conn_pool: queue.Queue = None
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
        conn.commit()
        pool.put(conn)
    _conn_pool = pool


def _get_conn() -> sqlite3.Connection:
    global _conn_pool, _pool_lock
    with _pool_lock:
        if _conn_pool is None:
            _init_pool()
    return _conn_pool.get()


def _put_conn(conn: sqlite3.Connection):
    _conn_pool.put(conn)


def track(name: str, category: str = "page_view"):
    global _last_cleanup
    now = time.time()
    conn = None
    try:
        conn = _get_conn()
        conn.execute(
            "INSERT INTO events (name, category, ts) VALUES (?, ?, ?)",
            (name, category, datetime.now(UTC).isoformat()),
        )
        conn.commit()

        if now - _last_cleanup > _BATCH_INTERVAL:
            _cleanup_old_events()
            _last_cleanup = now
    except Exception:
        logger.exception("Failed to track analytics event")
    finally:
        if conn:
            _put_conn(conn)


def get_counts(limit: int = 50) -> dict:
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.execute(
            "SELECT name, COUNT(*) as cnt FROM events GROUP BY name ORDER BY cnt DESC LIMIT ?",
            (limit,),
        )
        return dict(cursor.fetchall())
    except Exception:
        logger.exception("Failed to get analytics counts")
        return {}
    finally:
        if conn:
            _put_conn(conn)


def _cleanup_old_events():
    conn = None
    try:
        cutoff = (datetime.now(UTC) - timedelta(days=_RETENTION_DAYS)).isoformat()
        conn = _get_conn()
        conn.execute("DELETE FROM events WHERE ts < ?", (cutoff,))
        conn.commit()
    except Exception:
        logger.exception("Failed to cleanup old analytics events")
    finally:
        if conn:
            _put_conn(conn)
