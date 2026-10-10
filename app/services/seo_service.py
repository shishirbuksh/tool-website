"""SEO metadata service: builds ToolSEO objects from YAML data with category-based defaults."""

import time
from typing import Any

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.config import settings as _global_settings
from app.core.i18n import localize_path, normalize_locale
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
        base = (self.site_url or (_global_settings.SITE_URL if _global_settings and _global_settings.SITE_URL else "https://www.storybrainai.com")).rstrip("/")
        return f"{base}{localize_path(f'/tool/{self.slug}', self.locale or 'en')}"

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


class SeoService:

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: dict[str, tuple[float, dict[str, ToolSEO]]] = {}
        self.CACHE_TTL = 300

    def _is_cache_valid(self, locale: str = "en") -> bool:
        entry = self._cache.get(locale)
        return entry is not None and (time.time() - entry[0]) < self.CACHE_TTL

    def get_seo(self, slug: str, locale: str = "en") -> ToolSEO:
        loc = normalize_locale(locale)
        # Populate/refresh cache once, then lookup (avoids repeated builds).
        seo_map = self.get_seo_map(loc)
        if slug in seo_map:
            return seo_map[slug]
        return self._build_default(slug, loc)

    def _build_seo(self, slug: str, locale: str = "en") -> ToolSEO:
        raw = ToolDataLoader.get(slug)
        if raw:
            return self._from_raw(slug, raw, locale=locale)
        return self._build_default(slug, locale)

    def _localized_raw(self, raw: dict[str, Any], locale: str) -> dict[str, Any]:
        if locale == "en":
            return raw
        i18n = raw.get("i18n") or {}
        over = i18n.get(locale) if isinstance(i18n, dict) else None
        if not isinstance(over, dict):
            return raw
        merged = dict(raw)
        for k in ("name", "meta_title", "description", "keywords", "faqs", "howto_steps", "howto_calculate", "about_title", "about_body"):
            if over.get(k) not in (None, "", []):
                merged[k] = over[k]
        return merged

    def _from_raw(self, slug: str, raw: dict[str, Any], all_tools: dict[str, Any] | None = None, locale: str = "en") -> ToolSEO:
        raw = self._localized_raw(raw, locale)
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
                    "url": localize_path(f"/tool/{s}", locale),
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
        # Unify app_category mapping via _CATEGORY_APP unless explicitly set.
        app_category = raw.get("app_category") or _CATEGORY_APP.get(cat, "UtilitiesApplication")
        return ToolSEO(
            slug=slug,
            name=name,
            meta_title=meta_title,
            icon=raw.get("icon", "wand-2"),
            description=raw.get("description", ""),
            keywords=raw.get("keywords", []),
            app_category=app_category,
            app_sub_category=raw.get("app_sub_category", ""),
            image_url=raw.get("image_url") or _CATEGORY_IMAGE.get(cat, ""),
            faqs=raw.get("faqs", []),
            howto_steps=raw.get("howto_steps", []),
            howto_calculate=raw.get("howto_calculate", ""),
            about_title=raw.get("about_title", ""),
            about_body=raw.get("about_body", ""),
            date_modified=raw.get("date_modified", ""),
            related_slugs=related_slugs,
            related=related,
            site_url=self.settings.SITE_URL,
            locale=locale,
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
            locale=locale,
        )

    def get_seo_map(self, locale: str = "en") -> dict[str, ToolSEO]:
        """Build and cache ToolSEO for all tools (per locale)."""
        loc = normalize_locale(locale)
        if self._is_cache_valid(loc):
            assert loc in self._cache
            return self._cache[loc][1]
        all_data = ToolDataLoader.get_all()
        result: dict[str, ToolSEO] = {}
        for slug in all_data:
            result[slug] = self._from_raw(slug, all_data[slug], all_data, locale=loc)
        self._cache[loc] = (time.time(), result)
        return result


SEOService = SeoService


