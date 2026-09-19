"""Pytest fixtures: isolated settings, temp analytics DB, and test client."""

import os

import pytest

from app.core.config import Settings


@pytest.fixture
def settings():
    return Settings()


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Isolate SQLite analytics to tmp_path so tests never touch prod var/data."""
    db_file = tmp_path / "test_analytics.db"
    monkeypatch.setenv("ENV", "test")
    import app.services.analytics_service as svc

    old_path = svc.DB_PATH
    old_dir = svc.DATA_DIR
    svc.DB_PATH = str(db_file)
    svc.DATA_DIR = str(tmp_path)
    # Drain pooled connections bound to old path.
    try:
        svc._drain_pool()
    except Exception:
        pass
    yield str(db_file)
    try:
        svc._drain_pool()
    except Exception:
        pass
    svc.DB_PATH = old_path
    svc.DATA_DIR = old_dir


@pytest.fixture
def client(isolated_db):
    """Function-scoped TestClient with lifespan, loopback client for internal guards."""
    # Ensure hermetic env for app import side-effects.
    os.environ.setdefault("ENV", "test")
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 80)) as c:
        yield c
    # Reset global rate-limit / cache state to avoid order-dependence.
    try:
        from app.main import app as _app

        for mw in _app.user_middleware:
            inst = getattr(mw, "cls", None)
        # Best-effort: clear in-memory rate windows via middleware instances is not
        # directly reachable; rely on function scope + tmp DB for isolation.
    except Exception:
        pass

