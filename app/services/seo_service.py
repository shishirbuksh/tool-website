"""SEO metadata service: builds ToolSEO objects from YAML data with category-based defaults."""

import os
import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.config import settings as _global_settings
from app.core.tool_data import ToolDataLoader


class ToolSEO(BaseModel):
    slug: str
    name: str
    meta_title: str = ""
    icon: str = "wand-2"
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    app_category: str = "UtilitiesApplication"
    app_sub_category: str = ""
    image_url: str = ""
    faqs: list[dict[str, Any]] = Field(default_factory=list)
    howto_steps: list[dict[str, Any]] = Field(default_factory=list)
    howto_calculate: str = ""
    about_title: str = ""
    about_body: str = ""
    date_modified: str = ""
    related_slugs: list[str] = Field(default_factory=list)
    related: list[dict[str, Any]] = Field(default_factory=list)
    site_url: str = ""
    locale: str = "en"

    @property
    def url(self) -> str:
        base = (
            self.site_url
            or (
                _global_settings.SITE_URL
                if _global_settings and _global_settings.SITE_URL
                else "https://www.storybrainai.com"
            )
        ).rstrip("/")
        return f"{base}/tool/{self.slug}"

    @property
    def bare_path(self) -> str:
        return f"/tool/{self.slug}"


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

_CATEGORY_IMAGE: dict[str, str] = {
    "AI & Crypto": "/static/og-ai-tools.webp",
    "Image Processing": "/static/og-image-tools.webp",
    "Calculators": "/static/og-calculators.webp",
    "Developer & SEO": "/static/og-developer-tools.webp",
    "Business & Operations": "/static/og-business-tools.webp",
    "Productivity & Utilities": "/static/og-productivity-tools.webp",
}

_TOOL_OG_FILES: set[str] | None = None


def _tool_og_url(static_dir: str, slug: str) -> str:
    global _TOOL_OG_FILES
    if _TOOL_OG_FILES is None:
        try:
            _TOOL_OG_FILES = set(os.listdir(os.path.join(static_dir, "og", "t")))
        except OSError:
            _TOOL_OG_FILES = set()
    return f"/static/og/t/{slug}.webp" if f"{slug}.webp" in _TOOL_OG_FILES else ""


class SeoService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: dict[str, tuple[float, dict[str, ToolSEO]]] = {}
        self.CACHE_TTL = 300

    def _is_cache_valid(self, locale: str = "en") -> bool:
        entry = self._cache.get("en")
        return entry is not None and (time.time() - entry[0]) < self.CACHE_TTL

    def get_seo(self, slug: str, locale: str = "en") -> ToolSEO:
        seo_map = self.get_seo_map("en")
        if slug in seo_map:
            return seo_map[slug]
        return self._build_default(slug, "en")

    def _build_seo(self, slug: str, locale: str = "en") -> ToolSEO:
        raw = ToolDataLoader.get(slug)
        if raw:
            return self._from_raw(slug, raw, locale="en")
        return self._build_default(slug, "en")

    def _from_raw(
        self, slug: str, raw: dict[str, Any], all_tools: dict[str, Any] | None = None, locale: str = "en"
    ) -> ToolSEO:
        related_slugs = raw.get("related_slugs", [])
        if all_tools is None:
            all_tools = ToolDataLoader.get_all()
        related: list[dict[str, Any]] = []
        for s in related_slugs:
            tool_info = all_tools.get(s) if all_tools else None
            if isinstance(tool_info, dict):
                t_name = tool_info.get("name") or s.replace("-", " ").title()
                t_desc = tool_info.get("description", "")
            else:
                t_name = s.replace("-", " ").title()
                t_desc = ""
            related.append(
                {
                    "name": t_name,
                    "url": f"/tool/{s}",
                    "desc": t_desc,
                }
            )
        name = raw.get("name", slug.replace("-", " ").title())
        raw_meta_title = raw.get("meta_title", "")
        cat = raw.get("category", "")
        if not raw_meta_title:
            if cat in ("Calculators", "AI & Crypto", "Business & Operations"):
                meta_title = f"Free {name} Online | StoryBrain AI"
            elif cat in ("Developer & SEO",):
                meta_title = f"{name} — Free SEO Tool Online | StoryBrain AI"
            elif cat in ("Image Processing", "Productivity & Utilities"):
                meta_title = f"{name} - Fast & Private Browser Utility | StoryBrain AI"
            else:
                meta_title = f"{name} — Free Online Tool | StoryBrain AI"
        else:
            meta_title = raw_meta_title
        app_category = raw.get("app_category") or _CATEGORY_APP.get(cat, "UtilitiesApplication")
        try:
            static_dir = self.settings.static_dir
        except Exception:
            static_dir = ""
        return ToolSEO(
            slug=slug,
            name=name,
            meta_title=meta_title,
            icon=raw.get("icon", "wand-2"),
            description=raw.get("description", ""),
            keywords=raw.get("keywords", []),
            app_category=app_category,
            app_sub_category=raw.get("app_sub_category", ""),
            image_url=raw.get("image_url") or _tool_og_url(static_dir, slug) or _CATEGORY_IMAGE.get(cat, ""),
            faqs=raw.get("faqs", []),
            howto_steps=raw.get("howto_steps", []),
            howto_calculate=raw.get("howto_calculate", ""),
            about_title=raw.get("about_title", ""),
            about_body=raw.get("about_body", ""),
            date_modified=raw.get("date_modified", ""),
            related_slugs=related_slugs,
            related=related,
            site_url=self.settings.SITE_URL,
            locale="en",
        )

    def _build_default(self, slug: str, locale: str = "en") -> ToolSEO:
        name = slug.replace("-", " ").title()
        cat = "Productivity & Utilities"
        info = ToolDataLoader.get(slug)
        if info:
            cat = info.get("category", "Productivity & Utilities")
        return ToolSEO(
            slug=slug,
            name=name,
            meta_title=f"{name} - Fast & Private Browser Utility | StoryBrain AI",
            icon=_CATEGORY_ICONS.get(cat, "wand-2"),
            description=f"Free online {name} — fast, private, no-signup browser tool | StoryBrain AI",
            app_category=_CATEGORY_APP.get(cat, "UtilitiesApplication"),
            site_url=self.settings.SITE_URL,
            locale="en",
        )

    def get_seo_map(self, locale: str = "en") -> dict[str, ToolSEO]:
        if self._is_cache_valid("en"):
            return self._cache["en"][1]
        all_data = ToolDataLoader.get_all()
        result: dict[str, ToolSEO] = {}
        for slug in all_data:
            result[slug] = self._from_raw(slug, all_data[slug], all_data, locale="en")
        self._cache["en"] = (time.time(), result)
        return result


SEOService = SeoService
