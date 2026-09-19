"""Page-view analytics service: SQLite-backed, thread-safe, with batch writing and configurable retention."""

import asyncio
import os
import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta
from functools import partial
import queue

from app.core.config import settings
from app.core.log import get_logger

logger = get_logger(__name__)

DATA_DIR = os.path.join(settings.base_dir, "var", "data")
DB_PATH = os.path.join(DATA_DIR, "analytics.db")

_RETENTION_DAYS = settings.ANALYTICS_RETENTION_DAYS
_CLEANUP_INTERVAL = settings.ANALYTICS_CLEANUP_INTERVAL
_last_cleanup = 0.0
_cleanup_lock = threading.Lock()

_write_queue = queue.Queue(maxsize=100000)
_writer_thread = None
_writer_lock = threading.Lock()

_conn_pool: queue.Queue | None = None
_pool_lock = threading.Lock()


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _writer_worker():
    """Background thread that batches writes to SQLite to save IOPS."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=10000;")
    
    batch = []
    while True:
        try:
            item = _write_queue.get(timeout=1.0)
            if item is None:  # Shutdown signal
                break
            batch.append(item)
        except queue.Empty:
            pass
            
        # Drain the queue up to 500 items
        while not _write_queue.empty() and len(batch) < 500:
            try:
                item = _write_queue.get_nowait()
                if item is None:
                    break
                batch.append(item)
            except queue.Empty:
                break
                
        if batch:
            try:
                conn.executemany(
                    "INSERT INTO events_v2 (name, category, ts) VALUES (?, ?, ?)",
                    batch
                )
                conn.commit()
            except Exception:
                logger.exception("Failed to bulk insert analytics batch")
            finally:
                for _ in batch:
                    _write_queue.task_done()
                batch.clear()

        # Periodic retention cleanup on writer thread (avoids competing with pool conns).
        now_mono = time.monotonic()
        global _last_cleanup
        if now_mono - _last_cleanup > _CLEANUP_INTERVAL:
            with _cleanup_lock:
                if now_mono - _last_cleanup > _CLEANUP_INTERVAL:
                    _last_cleanup = now_mono
                    try:
                        cutoff_ts = int(time.time()) - (_RETENTION_DAYS * 86400)
                        conn.execute("DELETE FROM events_v2 WHERE ts < ?", (cutoff_ts,))
                        conn.execute("PRAGMA incremental_vacuum;")
                        conn.commit()
                    except Exception:
                        logger.exception("Failed to cleanup old analytics events")


def flush(timeout: float = 5.0) -> bool:
    """Block until queued analytics writes are persisted (for tests/scripts)."""
    try:
        _write_queue.join()
        return True
    except Exception:
        logger.exception("Failed to flush analytics queue")
        return False


def _init_pool() -> None:
    global _conn_pool, _writer_thread
    _ensure_dir()
    
    # Initialize the schema first
    init_conn = sqlite3.connect(DB_PATH, timeout=10.0)
    init_conn.execute("PRAGMA journal_mode=WAL;")
    init_conn.execute("PRAGMA auto_vacuum = INCREMENTAL;")
    init_conn.execute("PRAGMA mmap_size = 268435456;") # 256MB mmap
    init_conn.execute(
        "CREATE TABLE IF NOT EXISTS events_v2 ("
        "  id INTEGER PRIMARY KEY,"
        "  name TEXT NOT NULL,"
        "  category TEXT NOT NULL DEFAULT 'page_view',"
        "  ts INTEGER NOT NULL"
        ")"
    )
    init_conn.execute("CREATE INDEX IF NOT EXISTS idx_events_ts_name ON events_v2(ts, name)")
    init_conn.commit()
    init_conn.close()

    pool = queue.Queue(maxsize=5)
    for _ in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        conn.execute("PRAGMA mmap_size = 268435456;")
        pool.put(conn)
    _conn_pool = pool
    
    with _writer_lock:
        if _writer_thread is None or not _writer_thread.is_alive():
            _writer_thread = threading.Thread(target=_writer_worker, daemon=True)
            _writer_thread.start()


def _get_conn() -> sqlite3.Connection:
    global _conn_pool, _pool_lock
    with _pool_lock:
        if _conn_pool is None:
            _init_pool()
    try:
        return _conn_pool.get(timeout=10)
    except queue.Empty:
        raise RuntimeError("Analytics connection pool exhausted") from None


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
        try:
            conn.close()
        except Exception:
            pass


def _sanitize_field(value: str, max_len: int) -> str:
    s = str(value or "")
    s = s.replace("\r", " ").replace("\n", " ").strip()
    if len(s) > max_len:
        s = s[:max_len]
    return s


def track(name: str, category: str = "page_view") -> bool:
    global _last_cleanup, _conn_pool
    name = _sanitize_field(name, 200)
    if not name:
        return False
    category = _sanitize_field(category, 50) or "page_view"
    now_ts = int(time.time())
    
    # Initialize pool & writer if not done
    if _conn_pool is None:
         with _pool_lock:
            if _conn_pool is None:
                _init_pool()
                
    try:
        _write_queue.put_nowait((name, category, now_ts))
    except queue.Full:
        logger.warning("Analytics write queue is full, dropping event")
        return False

    return True


def get_counts(limit: int = 50) -> dict[str, int]:
    conn = None
    try:
        conn = _get_conn()
        cutoff_ts = int(time.time()) - (_RETENTION_DAYS * 86400)
        cursor = conn.execute(
            "SELECT name, COUNT(*) as cnt FROM events_v2 WHERE ts >= ? GROUP BY name ORDER BY cnt DESC LIMIT ?",
            (cutoff_ts, limit),
        )
        return dict(cursor.fetchall())
    except Exception:
        logger.exception("Failed to get analytics counts")
        return {}
    finally:
        if conn:
            _put_conn(conn)


def _cleanup_old_events() -> None:
    try:
        conn = _get_conn()
    except RuntimeError:
        return
    except Exception:
        return
    try:
        cutoff_ts = int(time.time()) - (_RETENTION_DAYS * 86400)
        conn.execute("DELETE FROM events_v2 WHERE ts < ?", (cutoff_ts,))
        conn.commit()
        try:
            conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
        except Exception:
            pass
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
