"""Configuration classes and dynamic asset versioning."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from django.conf import settings as _django_settings

_BASE_DIR = str(Path(__file__).resolve().parent.parent.parent)


class _FileHashCache:
    def __init__(self, paths: list[str]) -> None:
        self._paths = paths
        self._cached_sig: tuple[tuple[int, int] | None, ...] | None = None
        self._cached_digest: str = ""

    def digest(self) -> str:
        sigs: list[tuple[int, int] | None] = []
        for path in self._paths:
            try:
                st = os.stat(path)
                sigs.append((st.st_mtime_ns, st.st_size))
            except OSError:
                sigs.append(None)
        sig_tuple = tuple(sigs)
        if sig_tuple == self._cached_sig:
            return self._cached_digest
        if not any(sig_tuple):
            self._cached_digest = ""
            self._cached_sig = sig_tuple
            return ""
        hasher = hashlib.sha256()
        for path, sig in zip(self._paths, sig_tuple, strict=True):
            if sig is None:
                continue
            try:
                with open(path, "rb") as f:
                    hasher.update(f.read())
            except OSError:
                pass
        digest = hasher.hexdigest()[:8]
        self._cached_digest = digest
        self._cached_sig = sig_tuple
        return digest


class _DynamicAssetVersion:
    def __init__(self, static_dir: str) -> None:
        self._static_dir = static_dir
        self._hash_cache = _FileHashCache([
            os.path.join(static_dir, "css", "app.css"),
            os.path.join(static_dir, "js", "app.js"),
        ])

    def _bundle_digest(self) -> str:
        return self._hash_cache.digest()

    def _resolve(self) -> str:
        explicit = os.getenv("APP_VERSION", "").strip()
        base = explicit if explicit else "dev"
        digest = self._bundle_digest()
        if digest:
            return f"{base}-{digest}"
        return base

    def __str__(self) -> str:
        return self._resolve()

    def __repr__(self) -> str:
        return self._resolve()


class _DynamicAppCssHref:
    def __init__(self, static_dir: str, asset_version: _DynamicAssetVersion) -> None:
        self._static_dir = static_dir
        self._asset_version = asset_version
        self._hash_cache = _FileHashCache([os.path.join(static_dir, "css", "app.css")])

    def _resolve(self) -> str:
        digest = self._hash_cache.digest()
        if digest:
            hashed_name = f"app.{digest}.css"
            hashed_path = os.path.join(self._static_dir, "css", hashed_name)
            if os.path.isfile(hashed_path):
                return f"/static/css/{hashed_name}"
        return f"/static/css/app.css?v={self._asset_version}"

    def __str__(self) -> str:
        return self._resolve()

    def __repr__(self) -> str:
        return self._resolve()


class Settings:
    def __init__(self):
        self.base_dir = _BASE_DIR
        self.templates_dir = os.path.join(_BASE_DIR, "templates")
        self.static_dir = os.path.join(_BASE_DIR, "static")
        self.PROJECT_NAME = "Multi-Tool Website"
        self.SITE_URL = "https://www.storybrainai.com"
        self.CACHE_DEFAULT_TTL = 300
        self.ALLOWED_HOSTS = ""

    def __getattr__(self, name: str):
        if hasattr(_django_settings, name):
            return getattr(_django_settings, name)
        upper = name.upper()
        if hasattr(_django_settings, upper):
            return getattr(_django_settings, upper)
        raise AttributeError(f"'Settings' object has no attribute '{name}'")


settings = Settings()
