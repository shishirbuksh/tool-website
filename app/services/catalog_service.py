"""Tool catalog service: categorized tools and valid-tool slug list via ToolDataLoader."""

import os
import time

from app.core.config import Settings
from app.core.tool_data import ToolDataLoader


class CatalogService:
    CACHE_TTL = 300

    def __init__(self, settings: Settings):
        self.settings = settings
        self._cat_cache: tuple | None = None
        self._cat_cache_ts: float = 0

    def get_categorized_tools(self):
        now = time.time()
        if self._cat_cache is not None and now - self._cat_cache_ts < self.CACHE_TTL:
            return self._cat_cache
        categorized_tools = ToolDataLoader.get_categories()
        static_pages = []
        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        if os.path.exists(pages_dir):
            for f in os.listdir(pages_dir):
                if f.endswith(".html") and f != "sitemap.html":
                    name = f[:-5].replace("-", " ").title()
                    static_pages.append({"name": name, "url": f"/{f[:-5]}"})
        static_pages.sort(key=lambda x: x["name"])
        self._cat_cache = (categorized_tools, static_pages)
        self._cat_cache_ts = now
        return self._cat_cache

    def get_valid_tools(self):
        return ToolDataLoader.get_slugs()
