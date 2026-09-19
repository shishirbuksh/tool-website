"""Blog engine service: loads data/blog.yaml with TTL caching (mirrors SeoService/ToolDataLoader)."""

import os
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

    @property
    def url(self) -> str:
        base = (
            _global_settings.SITE_URL
            if _global_settings and _global_settings.SITE_URL
            else "https://www.storybrainai.com"
        )
        return f"{base.rstrip('/')}/blog/{self.pillar}/{self.slug}"


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
        path = self._ensure_blog_yaml()
        try:
            with open(path, "rb") as f:
                data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            return {}
        posts = data.get("posts", {})
        return posts if isinstance(posts, dict) else {}

    def _from_raw(self, slug: str, raw: dict[str, Any]) -> BlogPost:
        return BlogPost(
            slug=slug,
            pillar=str(raw.get("pillar", "")),
            title=str(raw.get("title", slug.replace("-", " ").title())),
            meta_title=str(raw.get("meta_title", "") or raw.get("title", "")),
            description=str(raw.get("description", "")),
            keywords=list(raw.get("keywords", []) or []),
            date_published=str(raw.get("date_published", "") or ""),
            date_modified=str(raw.get("date_modified", "") or ""),
            image=str(raw.get("image", "") or ""),
            faqs=list(raw.get("faqs", []) or []),
            howto_steps=list(raw.get("howto_steps", []) or []),
            body_html=str(raw.get("body_html", "") or ""),
            tools=list(raw.get("tools", []) or []),
            related_posts=list(raw.get("related_posts", []) or []),
        )

    def _get_post_map(self) -> dict[str, BlogPost]:
        if self._is_cache_valid():
            assert self._cache is not None
            return self._cache[1]
        raw = self._load_raw()
        result: dict[str, BlogPost] = {}
        for slug, info in raw.items():
            if isinstance(info, dict):
                result[str(slug)] = self._from_raw(str(slug), info)
        self._cache = (time.time(), result)
        return result

    def get_all(self) -> list[BlogPost]:
        posts = list(self._get_post_map().values())
        posts.sort(key=lambda p: (p.date_published or "", p.slug), reverse=True)
        return posts

    def get(self, slug: str) -> BlogPost | None:
        return self._get_post_map().get(slug)

    def get_by_pillar(self, pillar: str) -> list[BlogPost]:
        posts = [p for p in self._get_post_map().values() if p.pillar == pillar]
        posts.sort(key=lambda p: (p.date_published or "", p.slug), reverse=True)
        return posts

    def get_pillars(self) -> list[str]:
        pillars = sorted({p.pillar for p in self._get_post_map().values() if p.pillar})
        return pillars

    def get_recent(self, limit: int = 3) -> list[BlogPost]:
        """Newest posts by date_published (homepage Recent Guides)."""
        return self.get_all()[: max(0, limit)]

    def get_popular(self, limit: int = 3) -> list[BlogPost]:
        """Most in-depth/useful posts (homepage Popular Guides).

        Heuristic proxy for popularity without tracking: posts that link the most
        tools + most FAQs + longest body rank highest (most useful guides).
        Tiebreak by newest date_published. Deterministic, no analytics needed.
        """
        posts = list(self._get_post_map().values())

        def _score(p: BlogPost) -> tuple[int, str, str]:
            return (
                3 * len(p.tools) + len(p.faqs) + len(p.body_html) // 2000,
                p.date_published or "",
                p.slug,
            )

        posts.sort(key=_score, reverse=True)
        return posts[: max(0, limit)]


BlogEngineService = BlogService
