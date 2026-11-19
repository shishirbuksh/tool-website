"""High-throughput SQLite batch analytics service."""

from __future__ import annotations

import contextlib
import logging
import os
import queue
import sqlite3
import threading
import time
from django.conf import settings

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(settings.BASE_DIR, "var", "data")
DB_PATH = os.path.join(DATA_DIR, "analytics.db")

_RETENTION_DAYS = 90
_CLEANUP_INTERVAL = 300
_last_cleanup = 0.0
_cleanup_lock = threading.Lock()

_write_queue: queue.Queue = queue.Queue(maxsize=100000)
_writer_thread: threading.Thread | None = None
_writer_lock = threading.Lock()

_conn_pool: queue.Queue | None = None
_pool_lock = threading.Lock()


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _writer_worker() -> None:
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=10000;")

    batch = []
    while True:
        try:
            item = _write_queue.get(timeout=1.0)
            if item is None:
                break
            batch.append(item)
        except queue.Empty:
            pass

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
                conn.executemany("INSERT INTO events_v2 (name, category, ts) VALUES (?, ?, ?)", batch)
                conn.commit()
            except Exception:
                logger.exception("Failed to bulk insert analytics batch")
            finally:
                for _ in batch:
                    _write_queue.task_done()
                batch.clear()


def flush(timeout: float = 5.0) -> bool:
    """Block until queued analytics writes are persisted (for tests/scripts)."""
    try:
        _write_queue.join()
        return True
    except Exception:
        logger.exception("Failed to flush analytics queue")
        return False


def _drain_pool() -> None:
    global _conn_pool
    pool = _conn_pool
    if pool is not None:
        try:
            while True:
                c = pool.get_nowait()
                c.close()
        except queue.Empty:
            pass
    _conn_pool = None


def _init_pool() -> None:
    global _conn_pool, _writer_thread
    _ensure_dir()

    init_conn = sqlite3.connect(DB_PATH, timeout=10.0)
    init_conn.execute("PRAGMA journal_mode=WAL;")
    init_conn.execute("PRAGMA auto_vacuum = INCREMENTAL;")
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

    pool: queue.Queue = queue.Queue(maxsize=5)
    for _ in range(5):
        conn = sqlite3.connect(DB_PATH, timeout=5.0, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=10000;")
        pool.put(conn)
    _conn_pool = pool

    with _writer_lock:
        if _writer_thread is None or not _writer_thread.is_alive():
            _writer_thread = threading.Thread(target=_writer_worker, daemon=True)
            _writer_thread.start()


def _get_conn() -> sqlite3.Connection:
    global _conn_pool
    with _pool_lock:
        if _conn_pool is None:
            _init_pool()
    try:
        assert _conn_pool is not None
        return _conn_pool.get(timeout=10)
    except queue.Empty:
        raise RuntimeError("Analytics connection pool exhausted") from None


def _put_conn(conn: sqlite3.Connection | None) -> None:
    if conn is None:
        return
    try:
        if _conn_pool is None:
            with contextlib.suppress(Exception):
                conn.close()
            return
        _conn_pool.put_nowait(conn)
    except queue.Full:
        with contextlib.suppress(Exception):
            conn.close()


def track(name: str, category: str = "page_view") -> bool:
    name = str(name or "")[:200].strip()
    if not name:
        return False
    category = str(category or "page_view")[:50].strip()
    now_ts = int(time.time())

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
