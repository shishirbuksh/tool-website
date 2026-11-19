"""Pytest fixtures: isolated settings, temp analytics DB, and Django test client."""

import os
import json
import pytest
from django.conf import settings as django_settings
from django.test import Client


class DjangoTestClientWrapper:
    """Wraps Django Client to match Starlette TestClient signature used across tests."""

    def __init__(self, client=None):
        self._client = client or Client()

    def _prepare_kwargs(self, kwargs, follow_redirects=False, follow=False, headers=None):
        follow_final = follow or follow_redirects
        extra = {}
        if headers:
            for k, v in headers.items():
                if k.lower() == "host":
                    extra["HTTP_HOST"] = v
                else:
                    extra[k] = v
            extra["headers"] = headers
        kwargs["follow"] = follow_final
        kwargs.update(extra)
        return kwargs

    def get(self, path, *args, follow_redirects=False, follow=False, headers=None, **kwargs):
        kw = self._prepare_kwargs(kwargs, follow_redirects, follow, headers)
        resp = self._client.get(path, *args, **kw)
        if resp.status_code == 404 and b"<title>Not Found</title>" in resp.content:
            from config.urls import handler404_view
            req = getattr(resp, "wsgi_request", None)
            if req:
                return handler404_view(req)
        return resp

    def post(self, path, data=None, json=None, *args, follow_redirects=False, follow=False, headers=None, **kwargs):
        kw = self._prepare_kwargs(kwargs, follow_redirects, follow, headers)
        if json is not None:
            kw["content_type"] = "application/json"
            data = json
        return self._client.post(path, data=data, *args, **kw)

    def head(self, path, *args, follow_redirects=False, follow=False, headers=None, **kwargs):
        kw = self._prepare_kwargs(kwargs, follow_redirects, follow, headers)
        return self._client.head(path, *args, **kw)

    def put(self, path, data=None, json=None, *args, follow_redirects=False, follow=False, headers=None, **kwargs):
        kw = self._prepare_kwargs(kwargs, follow_redirects, follow, headers)
        if json is not None:
            kw["content_type"] = "application/json"
            data = json
        return self._client.put(path, data=data, *args, **kw)

    def delete(self, path, *args, follow_redirects=False, follow=False, headers=None, **kwargs):
        kw = self._prepare_kwargs(kwargs, follow_redirects, follow, headers)
        return self._client.delete(path, *args, **kw)

    def options(self, path, *args, follow_redirects=False, follow=False, headers=None, **kwargs):
        kw = self._prepare_kwargs(kwargs, follow_redirects, follow, headers)
        return self._client.options(path, *args, **kw)


class SettingsProxy:
    """Case-tolerant proxy for Django settings to support legacy tests."""
    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        if hasattr(self._target, name):
            return getattr(self._target, name)
        upper_name = name.upper()
        if hasattr(self._target, upper_name):
            return getattr(self._target, upper_name)
        raise AttributeError(f"'Settings' object has no attribute '{name}'")


@pytest.fixture
def settings():
    return SettingsProxy(django_settings)


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """Isolate SQLite analytics to tmp_path so tests never touch prod var/data."""
    db_file = tmp_path / "test_analytics.db"
    monkeypatch.setenv("ENV", "test")
    try:
        import apps.analytics.services as svc
        old_path = svc.DB_PATH
        old_dir = svc.DATA_DIR
        svc.DB_PATH = str(db_file)
        svc.DATA_DIR = str(tmp_path)
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
    except ImportError:
        yield str(db_file)


@pytest.fixture
def client(isolated_db):
    """Function-scoped Django test client."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    return DjangoTestClientWrapper()
