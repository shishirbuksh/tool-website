"""Singleton YAML-based tool data loader with TTL caching."""

import os
import time
from typing import Any

import yaml

from app.core.config import settings


class ToolDataLoader:
    _data: dict[str, Any] | None = None
    _cache_ts: float = 0
    CACHE_TTL: int = 300

    @classmethod
    def _load(cls) -> dict[str, Any]:
        now = time.time()
        if cls._data is not None and now - cls._cache_ts < cls.CACHE_TTL:
            return cls._data
        path = os.path.join(settings.base_dir, "data", "tools.yaml")
        with open(path, "rb") as f:
            cls._data = yaml.safe_load(f)["tools"]
        cls._cache_ts = now
        return cls._data

    @classmethod
    def get_all(cls) -> dict[str, Any]:
        return cls._load()

    @classmethod
    def get_slugs(cls) -> list[str]:
        return sorted(cls._load().keys())

    @classmethod
    def get(cls, slug: str) -> dict[str, Any] | None:
        return cls._load().get(slug)

    @classmethod
    def get_categories(cls) -> dict[str, list[dict[str, str]]]:
        data = cls._load()
        cats: dict[str, list[dict[str, str]]] = {}
        for slug, info in data.items():
            cat = info["category"]
            if cat not in cats:
                cats[cat] = []
            cats[cat].append({
                "name": info["name"],
                "url": f"/tool/{slug}",
                "desc": info["description"],
            })
        for cat in cats:
            cats[cat].sort(key=lambda x: x["name"])
        return dict(sorted(cats.items()))

    @classmethod
    def get_priority(cls, slug: str) -> float:
        info = cls._load().get(slug)
        if info:
            return info.get("sitemap_priority", 0.7)
        return 0.7
