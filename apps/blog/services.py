"""Blog repository service for loading data/blog.yaml."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any
import yaml
from django.conf import settings

_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


@dataclass
class BlogPost:
    slug: str
    pillar: str
    title: str
    meta_title: str = ""
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    date_published: str = ""
    date_modified: str = ""
    author: str = ""
    reviewed_by: str = ""
    sources: list[dict[str, str]] = field(default_factory=list)
    image: str = ""
    faqs: list[dict[str, Any]] = field(default_factory=list)
    howto_steps: list[dict[str, Any]] = field(default_factory=list)
    body_html: str = ""
    tools: list[str] = field(default_factory=list)
    related_posts: list[str] = field(default_factory=list)
    noindex: bool = False
    locale: str = "en"

    @property
    def url(self) -> str:
        base = getattr(settings, "SITE_URL", "https://www.storybrainai.com").rstrip("/")
        return f"{base}/blog/{self.pillar}/{self.slug}"


_POST_OG_FILES: set[str] | None = None


def _post_og_url(static_dir: str, slug: str) -> str:
    global _POST_OG_FILES
    if _POST_OG_FILES is None:
        try:
            _POST_OG_FILES = set(os.listdir(os.path.join(static_dir, "og", "p")))
        except OSError:
            _POST_OG_FILES = set()
    return f"/static/og/p/{slug}.webp" if f"{slug}.webp" in _POST_OG_FILES else ""


class Pillar(str):
    @property
    def slug(self) -> str:
        return str(self)

    @property
    def name(self) -> str:
        return str(self).replace("-", " ").title()

    @property
    def url(self) -> str:
        return f"/blog/{self}"

    def __getitem__(self, item):
        if item == "slug":
            return self.slug
        if item == "name":
            return self.name
        if item == "url":
            return self.url
        return super().__getitem__(item)


class BlogService:
    CACHE_TTL = 300
    _lock = threading.Lock()
    _cache: tuple[float, dict[str, BlogPost], list[BlogPost]] | None = None

    def __init__(self, settings=None) -> None:
        self.settings = settings

    def _load(self) -> tuple[dict[str, BlogPost], list[BlogPost]]:
        now = time.time()
        if self._cache is not None and now - self._cache[0] < self.CACHE_TTL:
            return self._cache[1], self._cache[2]

        with self._lock:
            now = time.time()
            if self._cache is not None and now - self._cache[0] < self.CACHE_TTL:
                return self._cache[1], self._cache[2]

            path = os.path.join(settings.BASE_DIR, "data", "blog.yaml")
            try:
                with open(path, "rb") as f:
                    raw = yaml.load(f, Loader=_YAML_LOADER)
            except Exception:
                raw = {}

            posts_raw = raw.get("posts", {}) if isinstance(raw, dict) else {}
            post_map: dict[str, BlogPost] = {}
            post_list: list[BlogPost] = []
            static_dir = getattr(settings, "STATIC_DIR", os.path.join(settings.BASE_DIR, "static"))

            for slug, item in posts_raw.items():
                og_url = _post_og_url(static_dir, slug)
                img = og_url or item.get("image", "/static/og-image.webp")
                bp = BlogPost(
                    slug=slug,
                    pillar=item.get("pillar", "general"),
                    title=item.get("title", slug.replace("-", " ").title()),
                    meta_title=item.get("meta_title", ""),
                    description=item.get("description", ""),
                    keywords=item.get("keywords", []),
                    date_published=item.get("date_published", ""),
                    date_modified=item.get("date_modified", ""),
                    author=item.get("author", "StoryBrain AI"),
                    reviewed_by=item.get("reviewed_by", "StoryBrain AI Editorial Team"),
                    sources=item.get("sources", []),
                    image=img,
                    faqs=item.get("faqs", []),
                    howto_steps=item.get("howto_steps", []),
                    body_html=item.get("body_html", ""),
                    tools=item.get("tools", []),
                    related_posts=item.get("related_posts", []),
                    noindex=item.get("noindex", False),
                )
                post_map[slug] = bp
                post_list.append(bp)

            self._cache = (now, post_map, post_list)
            return post_map, post_list

    def get_all(self) -> list[BlogPost]:
        _, post_list = self._load()
        return post_list

    def get(self, slug: str, locale: str = "en") -> BlogPost | None:
        post_map, _ = self._load()
        return post_map.get(slug)

    def get_post(self, pillar: str, slug: str) -> BlogPost | None:
        post_map, _ = self._load()
        p = post_map.get(slug)
        if p and p.pillar == pillar:
            return p
        return None

    def get_by_pillar(self, pillar: str) -> list[BlogPost]:
        _, post_list = self._load()
        return [p for p in post_list if p.pillar == pillar]

    def get_recent(self, limit: int = 3) -> list[BlogPost]:
        all_posts = self.get_all()
        sorted_posts = sorted(all_posts, key=lambda x: x.date_published or "1970-01-01", reverse=True)
        return sorted_posts[:limit]

    def get_popular(self, limit: int = 3) -> list[BlogPost]:
        # Return featured or recent posts
        return self.get_recent(limit)

    def get_pillars(self) -> list[Pillar]:
        all_posts = self.get_all()
        pillar_set = sorted({p.pillar for p in all_posts})
        return [Pillar(p) for p in pillar_set]

    def get_posts_for_tool(self, tool_slug: str, limit: int = 3) -> list[BlogPost]:
        all_posts = self.get_all()
        matched = []
        for p in all_posts:
            if tool_slug in p.tools:
                matched.append(p)
        if len(matched) < limit:
            # Fallback by keyword overlap or general guides
            for p in all_posts:
                if p not in matched and tool_slug.replace("-", " ") in p.title.lower():
                    matched.append(p)
        return matched[:limit]
