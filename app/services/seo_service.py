"""SEO metadata service: builds ToolSEO objects from YAML data with category-based defaults."""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.tool_data import ToolDataLoader


class ToolSEO(BaseModel):
    slug: str
    name: str
    meta_title: str = ""
    icon: str = "wand-2"
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    app_category: str = "UtilitiesApplication"
    faqs: list[dict] = Field(default_factory=list)
    howto_steps: list[dict] = Field(default_factory=list)
    howto_calculate: str = ""
    about_title: str = ""
    about_body: str = ""
    date_modified: str = ""
    related_slugs: list[str] = Field(default_factory=list)
    related: list[dict] = Field(default_factory=list)


_CATEGORY_ICONS: dict[str, str] = {
    "AI & Crypto": "bitcoin",
    "Image Processing": "image",
    "Calculators": "calculator",
    "Developer & SEO": "code",
    "Business & Operations": "briefcase",
    "Productivity & Utilities": "zap",
}

_CATEGORY_APP: dict[str, str] = {
    "AI & Crypto": "FinanceApplication",
    "Image Processing": "MultimediaApplication",
    "Calculators": "FinanceApplication",
    "Developer & SEO": "DeveloperApplication",
    "Business & Operations": "BusinessApplication",
    "Productivity & Utilities": "UtilitiesApplication",
}


class SeoService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._cache: tuple[float, dict[str, ToolSEO]] | None = None
        self.CACHE_TTL = 300

    def _is_cache_valid(self) -> bool:
        return self._cache is not None and (time.time() - self._cache[0]) < self.CACHE_TTL

    def get_seo(self, slug: str) -> ToolSEO:
        if self._is_cache_valid():
            return self._cache[1].get(slug) or self._build_default(slug)
        return self._build_seo(slug)

    def _build_seo(self, slug: str) -> ToolSEO:
        raw = ToolDataLoader.get(slug)
        if raw:
            return self._from_raw(slug, raw)
        return self._build_default(slug)

    def _from_raw(self, slug: str, raw: dict[str, Any]) -> ToolSEO:
        related_slugs = raw.get("related_slugs", [])
        all_tools = ToolDataLoader.get_all()
        related = [
            {
                "name": all_tools[s]["name"] if s in all_tools else s.replace("-", " ").title(),
                "url": f"/tool/{s}",
                "desc": all_tools[s].get("description", "") if s in all_tools else ""
            }
            for s in related_slugs
        ]
        name = raw.get("name", slug.replace("-", " ").title())
        raw_meta_title = raw.get("meta_title", "")
        if not raw_meta_title:
            cat = raw.get("category", "")
            if cat in ("Calculators", "AI & Crypto", "Business & Operations"):
                meta_title = f"Free {name} Online | StoryBrain AI"
            elif cat in ("Developer & SEO",):
                meta_title = f"{name} — Free SEO Tool Online | StoryBrain AI"
            elif cat in ("Image Processing", "Productivity & Utilities"):
                meta_title = f"Free {name} Online Tool | StoryBrain AI"
            else:
                meta_title = f"{name} — Free Online Tool | StoryBrain AI"
        else:
            meta_title = raw_meta_title
        return ToolSEO(
            slug=slug,
            name=name,
            meta_title=meta_title,
            icon=raw.get("icon", "wand-2"),
            description=raw.get("description", ""),
            keywords=raw.get("keywords", []),
            app_category=raw.get("app_category", "UtilitiesApplication"),
            faqs=raw.get("faqs", []),
            howto_steps=raw.get("howto_steps", []),
            howto_calculate=raw.get("howto_calculate", ""),
            about_title=raw.get("about_title", ""),
            about_body=raw.get("about_body", ""),
            date_modified=raw.get("date_modified", ""),
            related_slugs=related_slugs,
            related=related,
        )

    def _build_default(self, slug: str) -> ToolSEO:
        name = slug.replace("-", " ").title()
        cat = "Productivity & Utilities"
        info = ToolDataLoader.get(slug)
        if info:
            cat = info.get("category", "Productivity & Utilities")
        return ToolSEO(
            slug=slug,
            name=name,
            meta_title=f"Free {name} Online Tool | StoryBrain AI",
            icon=_CATEGORY_ICONS.get(cat, "wand-2"),
            description=f"Free online {name.lower()} utility",
            app_category=_CATEGORY_APP.get(cat, "UtilitiesApplication"),
        )

    def get_seo_map(self) -> dict[str, ToolSEO]:
        """Build and cache ToolSEO for all tools."""
        if self._is_cache_valid():
            return self._cache[1]
        all_data = ToolDataLoader.get_all()
        result: dict[str, ToolSEO] = {}
        for slug in all_data:
            result[slug] = self._from_raw(slug, all_data[slug])
        self._cache = (time.time(), result)
        return result
