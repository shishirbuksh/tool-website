"""Blog engine service: loads data/blog.yaml with TTL caching (mirrors SeoService/ToolDataLoader)."""

import os
import threading
import time
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.config import settings as _global_settings


class BlogPost(BaseModel):
    slug: str
    pillar: str
    title: str
    meta_title: str = ""
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    date_published: str = ""
    date_modified: str = ""
    image: str = ""
    faqs: list[dict[str, Any]] = Field(default_factory=list)
    howto_steps: list[dict[str, Any]] = Field(default_factory=list)
    body_html: str = ""
    tools: list[str] = Field(default_factory=list)
    related_posts: list[str] = Field(default_factory=list)
    locale: str = "en"

    @property
    def url(self) -> str:
        from app.core.i18n import localize_path as _lp  # noqa: PLC0415

        base = (
            _global_settings.SITE_URL
            if _global_settings and _global_settings.SITE_URL
            else "https://www.storybrainai.com"
        )
        return f"{base.rstrip('/')}{_lp(f'/blog/{self.pillar}/{self.slug}', self.locale or 'en')}"


_PLACEHOLDER_YAML = """posts:
  emi-calculator-guide:
    pillar: calculators
    title: EMI Calculator Guide
    meta_title: EMI Calculator Guide — How EMIs Work | StoryBrain AI
    description: Learn how EMI is calculated with a simple guide and free EMI calculator.
    keywords:
      - emi calculator guide
      - how emi is calculated
      - free emi calculator online
    date_published: '2026-01-15'
    date_modified: '2026-09-01'
    image: /static/og-image.webp
    faqs:
      - q: What is EMI?
        a: EMI (Equated Monthly Instalment) is a fixed monthly payment towards a loan.
      - q: Is this guide financial advice?
        a: No. This guide is for education only and is not financial advice.
    howto_steps:
      - title: Enter Loan Details
        desc: Type your loan amount, interest rate, and tenure into the calculator.
      - title: Review Your EMI
        desc: See your monthly EMI update instantly in your browser.
    body_html: '<p>TODO - content writers will fill this guide (placeholder under 100 words). EMI splits principal and interest into equal monthly payments.</p><p>Use our free EMI calculator to estimate payments. Verify figures with a qualified professional.</p>'
    tools:
      - emi-calculator
    related_posts: []
"""

_POST_OG_FILES: set[str] | None = None
_RAW_BLOG_LOCK = threading.Lock()
_RAW_BLOG_CACHE: tuple[float, dict[str, Any]] | None = None
_PARSED_POSTS_LOCK = threading.Lock()
_PARSED_POSTS_CACHE: dict[str, tuple[float, dict[str, BlogPost], list[BlogPost], list[BlogPost]]] = {}



def _post_og_url(static_dir: str, slug: str) -> str:
    """Per-post OG image (`static/og/p/<slug>.webp`, see scripts/generate_og.py).

    Existence scanned once per process; missing file -> "" (caller keeps the
    YAML image). Same image serves all locales (EN title art).
    """
    global _POST_OG_FILES
    if _POST_OG_FILES is None:
        try:
            _POST_OG_FILES = set(os.listdir(os.path.join(static_dir, "og", "p")))
        except OSError:
            _POST_OG_FILES = set()
    return f"/static/og/p/{slug}.webp" if f"{slug}.webp" in _POST_OG_FILES else ""


class BlogService:
    CACHE_TTL = 300

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._cache: tuple[float, dict[str, BlogPost]] | None = None

    def _blog_yaml_path(self) -> str:
        base = getattr(self.settings, "base_dir", None) or _global_settings.base_dir
        return os.path.join(base, "data", "blog.yaml")

    def _ensure_blog_yaml(self) -> str:
        path = self._blog_yaml_path()
        if not os.path.isfile(path):
            # data/ is read-only under systemd hardening: auto-creating would
            # silently serve an empty blog in prod. Fail fast instead.
            if self.settings.is_prod:
                msg = f"Blog data file not found: {path}"
                raise FileNotFoundError(msg)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(_PLACEHOLDER_YAML)
            except OSError:
                pass
        return path

    def _is_cache_valid(self) -> bool:
        return self._cache is not None and (time.time() - self._cache[0]) < self.CACHE_TTL

    def _load_raw(self) -> dict[str, Any]:
        global _RAW_BLOG_CACHE
        now = time.time()
        if _RAW_BLOG_CACHE is not None and (now - _RAW_BLOG_CACHE[0]) < self.CACHE_TTL:
            return _RAW_BLOG_CACHE[1]
        with _RAW_BLOG_LOCK:
            now = time.time()
            if _RAW_BLOG_CACHE is not None and (now - _RAW_BLOG_CACHE[0]) < self.CACHE_TTL:
                return _RAW_BLOG_CACHE[1]
            path = self._ensure_blog_yaml()
            try:
                with open(path, "rb") as f:
                    data = yaml.safe_load(f) or {}
            except FileNotFoundError:
                return {}
            posts = data.get("posts", {})
            result = posts if isinstance(posts, dict) else {}
            _RAW_BLOG_CACHE = (now, result)
            return result

    def _localized_raw(self, raw: dict[str, Any], locale: str) -> dict[str, Any]:
        if locale == "en":
            return raw
        i18n = raw.get("i18n") or {}
        over = i18n.get(locale) if isinstance(i18n, dict) else None
        if not isinstance(over, dict):
            return raw
        from app.core.content_sanitize import clean_localized_value  # noqa: PLC0415

        over = clean_localized_value(over)
        merged = dict(raw)
        for k in ("title", "meta_title", "description", "keywords", "faqs", "howto_steps", "body_html"):
            if over.get(k) not in (None, "", []):
                merged[k] = over[k]
        # Per-locale translation date (optional): sitemap lastmod reflects the
        # translation refresh, not the EN edit. date_published stays EN.
        if isinstance(over.get("date_modified"), str) and over.get("date_modified"):
            merged["date_modified"] = over["date_modified"]
        return merged

    def _from_raw(self, slug: str, raw: dict[str, Any], locale: str = "en") -> BlogPost:
        raw = self._localized_raw(raw, locale)
        try:
            static_dir = self.settings.static_dir
        except Exception:
            static_dir = ""
        return BlogPost(
            slug=slug,
            pillar=str(raw.get("pillar", "")),
            title=str(raw.get("title", slug.replace("-", " ").title())),
            meta_title=str(raw.get("meta_title", "") or raw.get("title", "")),
            description=str(raw.get("description", "")),
            keywords=list(raw.get("keywords", []) or []),
            date_published=str(raw.get("date_published", "") or ""),
            date_modified=str(raw.get("date_modified", "") or ""),
            image=_post_og_url(static_dir, slug) or str(raw.get("image", "") or ""),
            faqs=list(raw.get("faqs", []) or []),
            howto_steps=list(raw.get("howto_steps", []) or []),
            body_html=str(raw.get("body_html", "") or ""),
            tools=list(raw.get("tools", []) or []),
            related_posts=list(raw.get("related_posts", []) or []),
            locale=locale,
        )

    def _get_parsed_bundle(self, locale: str = "en") -> tuple[dict[str, BlogPost], list[BlogPost], list[BlogPost]]:
        from app.core.i18n import normalize_locale as _norm  # noqa: PLC0415

        loc = _norm(locale)
        now = time.time()
        cached = _PARSED_POSTS_CACHE.get(loc)
        if cached and (now - cached[0]) < self.CACHE_TTL:
            return cached[1], cached[2], cached[3]

        with _PARSED_POSTS_LOCK:
            now = time.time()
            cached = _PARSED_POSTS_CACHE.get(loc)
            if cached and (now - cached[0]) < self.CACHE_TTL:
                return cached[1], cached[2], cached[3]

            raw = self._load_raw()
            post_map: dict[str, BlogPost] = {}
            for slug, info in raw.items():
                if isinstance(info, dict):
                    post_map[str(slug)] = self._from_raw(str(slug), info, locale=loc)

            # Pre-sort all posts by newest published date
            all_posts = list(post_map.values())
            all_posts.sort(key=lambda p: (p.date_published or "", p.slug), reverse=True)

            # Pre-sort popular posts
            def _score(p: BlogPost) -> tuple[int, str, str]:
                return (
                    3 * len(p.tools) + len(p.faqs) + len(p.body_html) // 2000,
                    p.date_published or "",
                    p.slug,
                )

            popular_posts = list(post_map.values())
            popular_posts.sort(key=_score, reverse=True)

            _PARSED_POSTS_CACHE[loc] = (now, post_map, all_posts, popular_posts)
            if loc == "en":
                self._cache = (now, post_map)
            return post_map, all_posts, popular_posts

    def _get_post_map(self, locale: str = "en") -> dict[str, BlogPost]:
        post_map, _, _ = self._get_parsed_bundle(locale)
        return post_map

    def get_all(self, locale: str = "en") -> list[BlogPost]:
        _, all_posts, _ = self._get_parsed_bundle(locale)
        return list(all_posts)

    def get(self, slug: str, locale: str = "en") -> BlogPost | None:
        return self._get_post_map(locale).get(slug)

    def get_by_pillar(self, pillar: str, locale: str = "en") -> list[BlogPost]:
        all_posts = self.get_all(locale)
        return [p for p in all_posts if p.pillar == pillar]

    def get_pillars(self) -> list[str]:
        pillars = sorted({p.pillar for p in self._get_post_map().values() if p.pillar})
        return pillars

    def get_recent(self, limit: int = 3, locale: str = "en") -> list[BlogPost]:
        """Newest posts by date_published (homepage Recent Guides)."""
        return self.get_all(locale)[: max(0, limit)]

    def get_popular(self, limit: int = 3, locale: str = "en") -> list[BlogPost]:
        """Most in-depth/useful posts (homepage Popular Guides).

        Heuristic proxy for popularity without tracking: posts that link the most
        tools + most FAQs + longest body rank highest (most useful guides).
        Tiebreak by newest date_published. Deterministic, no analytics needed.
        """
        _, _, popular = self._get_parsed_bundle(locale)
        return popular[: max(0, limit)]



BlogEngineService = BlogService
