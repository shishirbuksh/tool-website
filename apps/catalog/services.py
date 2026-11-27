"""Tool catalog & SEO metadata services."""

from __future__ import annotations

import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any
import yaml
from django.conf import settings

from apps.core.constants import QUARANTINED_TOOLS

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@dataclass
class ToolSEO:
    slug: str
    name: str
    meta_title: str = ""
    icon: str = "wand-2"
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    app_category: str = "UtilitiesApplication"
    app_sub_category: str = ""
    image_url: str = ""
    faqs: list[dict[str, Any]] = field(default_factory=list)
    howto_steps: list[dict[str, Any]] = field(default_factory=list)
    howto_calculate: str = ""
    about_title: str = ""
    about_body: str = ""
    date_modified: str = ""
    author: str = ""
    reviewed_by: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    wikidata_id: str = ""
    noindex: bool = False
    related_slugs: list[str] = field(default_factory=list)
    related: list[dict[str, Any]] = field(default_factory=list)
    category: str = ""
    site_url: str = ""
    locale: str = "en"

    @property
    def url(self) -> str:
        base = getattr(settings, "SITE_URL", "https://www.storybrainai.com").rstrip("/")
        return f"{base}/tool/{self.slug}"

    @property
    def bare_path(self) -> str:
        return f"/tool/{self.slug}"


class ToolDataLoader:
    _data: dict[str, Any] | None = None
    _cache_ts: float = 0.0
    CACHE_TTL: int = 300
    _lock = threading.Lock()

    @classmethod
    def _load(cls) -> dict[str, Any]:
        now = time.time()
        if cls._data is not None and now - cls._cache_ts < cls.CACHE_TTL:
            return cls._data
        with cls._lock:
            now = time.time()
            if cls._data is not None and now - cls._cache_ts < cls.CACHE_TTL:
                return cls._data
            path = os.path.join(settings.BASE_DIR, "data", "tools.yaml")
            try:
                with open(path, "rb") as f:
                    loaded = yaml.load(f, Loader=_YAML_LOADER)
            except FileNotFoundError as e:
                raise FileNotFoundError(f"Tool data file not found: {path}") from e
            if not isinstance(loaded, dict) or not isinstance(loaded.get("tools"), dict):
                raise ValueError(f"Tool data malformed (missing 'tools' dict): {path}")
            cls._data = loaded["tools"]
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
            cat = info.get("category", "Other")
            if cat not in cats:
                cats[cat] = []
            cats[cat].append({
                "name": info.get("name", slug),
                "url": f"/tool/{slug}",
                "desc": info.get("description", ""),
                "icon": info.get("icon", "box"),
                "category": cat,
                "slug": slug,
            })
        for cat in cats:
            cats[cat].sort(key=lambda x: x["name"])
        return dict(sorted(cats.items()))


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


class CatalogService:
    CACHE_TTL = 300

    def __init__(self, settings=None) -> None:
        self.settings = settings
        self._cache: tuple[float, tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]] | None = None

    def get_categorized_tools(self) -> tuple[dict[str, list[dict[str, str]]], list[dict[str, str]]]:
        now = time.time()
        if self._cache is not None and now - self._cache[0] < self.CACHE_TTL:
            return self._cache[1]
        categorized_tools = ToolDataLoader.get_categories()
        static_pages: list[dict[str, str]] = []
        pages_dir = os.path.join(settings.BASE_DIR, "templates", "pages")
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
        self._cache = (now, payload)
        return payload

    def get_valid_tools(self) -> list[str]:
        return ToolDataLoader.get_slugs()


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
    def __init__(self, settings=None) -> None:
        self.settings = settings
        self._cache: tuple[float, dict[str, ToolSEO]] | None = None
        self.CACHE_TTL = 300

    def get_seo(self, slug: str, locale: str = "en") -> ToolSEO:
        now = time.time()
        if self._cache is not None and now - self._cache[0] < self.CACHE_TTL:
            if slug in self._cache[1]:
                return self._cache[1][slug]
        
        all_tools = ToolDataLoader.get_all()
        built: dict[str, ToolSEO] = {}
        for s, raw in all_tools.items():
            built[s] = self._from_raw(s, raw, all_tools)
        self._cache = (now, built)
        return built.get(slug) or self._build_default(slug)

    def _build_default(self, slug: str) -> ToolSEO:
        name = slug.replace("-", " ").title()
        return ToolSEO(slug=slug, name=name, meta_title=f"{name} — Free Online Tool")

    def _from_raw(self, slug: str, raw: dict[str, Any], all_tools: dict[str, Any] | None = None) -> ToolSEO:
        cat = raw.get("category", "")
        name = raw.get("name", slug.replace("-", " ").title())
        meta_title = raw.get("meta_title") or f"{name} — Free Online Tool"
        icon = raw.get("icon") or _CATEGORY_ICONS.get(cat, "wand-2")
        app_cat = raw.get("app_category") or _CATEGORY_APP.get(cat, "UtilitiesApplication")
        static_dir = getattr(settings, "STATIC_DIR", os.path.join(settings.BASE_DIR, "static"))
        og_url = _tool_og_url(static_dir, slug)
        img_url = og_url or raw.get("image_url") or _CATEGORY_IMAGE.get(cat, "/static/og-image.webp")

        rel_slugs = raw.get("related_slugs", [])
        related_items = []
        if all_tools:
            for rs in rel_slugs:
                if rs in all_tools and (slug in QUARANTINED_TOOLS or rs not in QUARANTINED_TOOLS):
                    rinfo = all_tools[rs]
                    related_items.append({
                        "name": rinfo.get("name", rs),
                        "url": f"/tool/{rs}",
                        "desc": rinfo.get("description", ""),
                        "icon": rinfo.get("icon", "box"),
                        "category": rinfo.get("category", ""),
                    })

        return ToolSEO(
            slug=slug,
            name=name,
            category=cat,
            meta_title=meta_title,
            icon=icon,
            description=raw.get("description", ""),
            keywords=raw.get("keywords", []),
            app_category=app_cat,
            app_sub_category=raw.get("app_sub_category", ""),
            image_url=img_url,
            faqs=raw.get("faqs", []),
            howto_steps=raw.get("howto_steps", []),
            howto_calculate=raw.get("howto_calculate", ""),
            about_title=raw.get("about_title", ""),
            about_body=raw.get("about_body", ""),
            date_modified=raw.get("date_modified", ""),
            author=raw.get("author", "StoryBrain AI"),
            reviewed_by=raw.get("reviewed_by", "StoryBrain AI Editorial Team"),
            sources=raw.get("sources", []),
            wikidata_id=raw.get("wikidata_id", ""),
            noindex=raw.get("noindex", False),
            related_slugs=rel_slugs,
            related=related_items,
        )


def tool_etag(tool_name: str, date_modified: str | None) -> str:
    raw = f"tool/{tool_name}:{date_modified or ''}:{settings.APP_VERSION}".encode()
    return 'W/"' + hashlib.sha1(raw).hexdigest()[:32] + '"'
