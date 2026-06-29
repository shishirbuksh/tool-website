"""Tool catalog service: categorized tools and valid-tool slug list via ToolDataLoader."""

import os

from app.core.config import Settings
from app.core.tool_data import ToolDataLoader


class CatalogService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cat_cache = None
        self._tools_cache = None

    def get_categorized_tools(self):
        if self._cat_cache is not None:
            return self._cat_cache
        self._cat_cache = self._build_categorized_tools()
        return self._cat_cache

    def _build_categorized_tools(self):
        categorized_tools = ToolDataLoader.get_categories()

        static_pages = []
        pages_dir = os.path.join(self.settings.templates_dir, "pages")
        if os.path.exists(pages_dir):
            for f in os.listdir(pages_dir):
                if f.endswith(".html") and f != "sitemap.html":
                    name = f[:-5].replace("-", " ").title()
                    static_pages.append({"name": name, "url": f"/{f[:-5]}"})
        static_pages.sort(key=lambda x: x["name"])

        return categorized_tools, static_pages

    def get_valid_tools(self):
        if self._tools_cache is not None:
            return self._tools_cache
        self._tools_cache = ToolDataLoader.get_slugs()
        return self._tools_cache
