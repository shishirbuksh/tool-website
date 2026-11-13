"""Blog engine service: loads data/blog.yaml with TTL caching (mirrors SeoService/ToolDataLoader)."""

import os
import threading
import time
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.config import settings as _global_settings

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class BlogPost(BaseModel):
    slug: str
    pillar: str
    title: str
    meta_title: str = ""
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    date_published: str = ""
    date_modified: str = ""
    author: str = ""
    reviewed_by: str = ""
    sources: list[dict[str, str]] = Field(default_factory=list)
    image: str = ""
    faqs: list[dict[str, Any]] = Field(default_factory=list)
    howto_steps: list[dict[str, Any]] = Field(default_factory=list)
    body_html: str = ""
    tools: list[str] = Field(default_factory=list)
    related_posts: list[str] = Field(default_factory=list)
    noindex: bool = False
    locale: str = "en"

    @property
    def url(self) -> str:
        base = (
            _global_settings.SITE_URL
            if _global_settings and _global_settings.SITE_URL
            else "https://www.storybrainai.com"
        )
        return f"{base.rstrip('/')}/blog/{self.pillar}/{self.slug}"


_POST_OG_FILES: set[str] | None = None
_RAW_BLOG_LOCK = threading.Lock()
_RAW_BLOG_CACHE: tuple[float, dict[str, Any]] | None = None
_PARSED_POSTS_LOCK = threading.Lock()
_PARSED_POSTS_CACHE: tuple[float, dict[str, BlogPost], list[BlogPost], list[BlogPost]] | None = None


def _post_og_url(static_dir: str, slug: str) -> str:
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

    def _load_raw(self) -> dict[str, Any]:
        global _RAW_BLOG_CACHE
        now = time.time()
        if _RAW_BLOG_CACHE is not None and (now - _RAW_BLOG_CACHE[0]) < self.CACHE_TTL:
            return _RAW_BLOG_CACHE[1]
        with _RAW_BLOG_LOCK:
            now = time.time()
            if _RAW_BLOG_CACHE is not None and (now - _RAW_BLOG_CACHE[0]) < self.CACHE_TTL:
                return _RAW_BLOG_CACHE[1]
            path = self._blog_yaml_path()
            try:
                with open(path, "rb") as f:
                    data = yaml.load(f, Loader=_YAML_LOADER) or {}
            except FileNotFoundError:
                return {}
            posts = data.get("posts", {})
            result = posts if isinstance(posts, dict) else {}
            _RAW_BLOG_CACHE = (now, result)
            return result

    def _from_raw(self, slug: str, raw: dict[str, Any], locale: str = "en") -> BlogPost:
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
            author=str(raw.get("author", "") or ""),
            reviewed_by=str(raw.get("reviewed_by", "") or ""),
            sources=[
                {"label": str(src.get("label") or src.get("url")), "url": str(src["url"])}
                for src in (raw.get("sources") or [])
                if isinstance(src, dict) and src.get("url")
            ],
            image=_post_og_url(static_dir, slug) or str(raw.get("image", "") or ""),
            faqs=list(raw.get("faqs", []) or []),
            howto_steps=list(raw.get("howto_steps", []) or []),
            body_html=str(raw.get("body_html", "") or ""),
            tools=list(raw.get("tools", []) or []),
            related_posts=list(raw.get("related_posts", []) or []),
            noindex=bool(raw.get("noindex", False)),
            locale="en",
        )

    def _get_parsed_bundle(self, locale: str = "en") -> tuple[dict[str, BlogPost], list[BlogPost], list[BlogPost]]:
        global _PARSED_POSTS_CACHE
        now = time.time()
        if _PARSED_POSTS_CACHE and (now - _PARSED_POSTS_CACHE[0]) < self.CACHE_TTL:
            return _PARSED_POSTS_CACHE[1], _PARSED_POSTS_CACHE[2], _PARSED_POSTS_CACHE[3]

        with _PARSED_POSTS_LOCK:
            now = time.time()
            if _PARSED_POSTS_CACHE and (now - _PARSED_POSTS_CACHE[0]) < self.CACHE_TTL:
                return _PARSED_POSTS_CACHE[1], _PARSED_POSTS_CACHE[2], _PARSED_POSTS_CACHE[3]

            raw = self._load_raw()
            post_map: dict[str, BlogPost] = {}
            for slug, info in raw.items():
                if isinstance(info, dict):
                    post_map[str(slug)] = self._from_raw(str(slug), info, locale="en")

            all_posts = list(post_map.values())
            all_posts.sort(key=lambda p: (p.date_published or "", p.slug), reverse=True)

            def _score(p: BlogPost) -> tuple[int, str, str]:
                return (
                    3 * len(p.tools) + len(p.faqs) + len(p.body_html) // 2000,
                    p.date_published or "",
                    p.slug,
                )

            popular_posts = list(post_map.values())
            popular_posts.sort(key=_score, reverse=True)

            _PARSED_POSTS_CACHE = (now, post_map, all_posts, popular_posts)
            self._cache = (now, post_map)
            return post_map, all_posts, popular_posts

    def _get_post_map(self, locale: str = "en") -> dict[str, BlogPost]:
        post_map, _, _ = self._get_parsed_bundle("en")
        return post_map

    def get_all(self, locale: str = "en") -> list[BlogPost]:
        _, all_posts, _ = self._get_parsed_bundle("en")
        return list(all_posts)

    def get(self, slug: str, locale: str = "en") -> BlogPost | None:
        return self._get_post_map("en").get(slug)

    def get_by_pillar(self, pillar: str, locale: str = "en") -> list[BlogPost]:
        all_posts = self.get_all("en")
        return [p for p in all_posts if p.pillar == pillar]

    def get_pillars(self) -> list[str]:
        pillars = sorted({p.pillar for p in self._get_post_map().values() if p.pillar})
        return pillars

    def get_recent(self, limit: int = 3, locale: str = "en") -> list[BlogPost]:
        return self.get_all("en")[: max(0, limit)]

    def get_popular(self, limit: int = 3, locale: str = "en") -> list[BlogPost]:
        _, _, popular = self._get_parsed_bundle("en")
        return popular[: max(0, limit)]

    def get_posts_for_tool(self, tool_slug: str, limit: int = 3, locale: str = "en") -> list[BlogPost]:
        all_posts = self.get_all(locale)
        # Direct tool matches first
        matching = [p for p in all_posts if tool_slug in p.tools]
        if len(matching) < limit:
            seen = {p.slug for p in matching}
            token = tool_slug.replace("-", " ").lower()
            for p in all_posts:
                if p.slug not in seen and (token in p.title.lower() or tool_slug in p.slug):
                    matching.append(p)
                    seen.add(p.slug)
                    if len(matching) >= limit:
                        break
        return matching[:limit]


BlogEngineService = BlogService
