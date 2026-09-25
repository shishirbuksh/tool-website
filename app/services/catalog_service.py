"""Tool catalog service: categorized tools and valid-tool slug list via ToolDataLoader."""

import os
import time

from app.core.config import Settings
from app.core.tool_data import ToolDataLoader

# Module-level memoization for categorized tools (ROUND-2 perf fix):
# shared across all CatalogService instances, TTL 300s.
_CACHE_TTL = 300
_CACHE: tuple[float, tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]] | None = None


class CatalogService:
    CACHE_TTL = 300

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cat_cache: tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]] | None = None
        self._cat_cache_ts: float = 0.0

    def get_categorized_tools(self) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]:
        global _CACHE
        now = time.time()
        if _CACHE is not None:
            ts, payload = _CACHE
            if now - ts < _CACHE_TTL:
                # Return same ref (not deepcopy) for perf; callers treat as read-only.
                return payload
        categorized_tools = ToolDataLoader.get_categories()
        static_pages: list[dict[str, str]] = []
        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        if os.path.exists(pages_dir):
            try:
                entries = os.listdir(pages_dir)
            except OSError:
                entries = []
            for f in entries:
                if f.endswith(".html") and f not in ("sitemap.html", "404.html", "500.html", "offline.html"):
                    name = f[:-5].replace("-", " ").title()
                    static_pages.append({"name": name, "url": f"/{f[:-5]}"})
        static_pages.sort(key=lambda x: x["name"])
        payload = (categorized_tools, static_pages)
        _CACHE = (now, payload)
        # Keep instance fields in sync for backwards-compat / introspection.
        self._cat_cache = payload
        self._cat_cache_ts = now
        # Return same ref (not deepcopy) for perf; callers treat as read-only.
        return payload

    def get_valid_tools(self) -> list[str]:
        return ToolDataLoader.get_slugs()

