"""Tool catalog service: categorized tools and valid-tool slug list via ToolDataLoader."""

import os
import time

from app.core.config import Settings
from app.core.i18n import localize_path, normalize_locale
from app.core.tool_data import ToolDataLoader

# Module-level memoization for categorized tools (ROUND-2 perf fix):
# shared across all CatalogService instances, TTL 300s.
_CACHE_TTL = 300
_CACHE: tuple[float, tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]] | None = None
# Per-locale caches for translated catalogs (pilot tools translated, rest EN fallback).
_LOCALE_CACHE: dict[str, tuple[float, tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]]] = {}


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

    def get_categorized_tools_localized(
        self, locale: str = "en"
    ) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]:
        """Categorized tools with translated name/desc/url for pilot tools (EN fallback)."""
        loc = normalize_locale(locale)
        if loc == "en":
            return self.get_categorized_tools()
        now = time.time()
        entry = _LOCALE_CACHE.get(loc)
        if entry and now - entry[0] < _CACHE_TTL:
            return entry[1]
        data = ToolDataLoader.get_all()
        cats: dict[str, list[dict[str, str]]] = {}
        for slug, info in data.items():
            over = ((info.get("i18n") or {}).get(loc) or {}) if isinstance(info, dict) else {}
            cat = info.get("category", "")
            cats.setdefault(cat, []).append(
                {
                    "name": over.get("name") or info.get("name", ""),
                    "url": localize_path(f"/tool/{slug}", loc),
                    "desc": over.get("description") or info.get("description", ""),
                }
            )
        for cat in cats:
            cats[cat].sort(key=lambda x: x["name"])
        payload = (dict(sorted(cats.items())), self.get_categorized_tools()[1])
        _LOCALE_CACHE[loc] = (now, payload)
        return payload
