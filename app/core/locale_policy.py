"""Locale release policy: the single source of truth for localized indexability.

Indexing a localized URL requires two independent gates:

1. The locale is released in ``data/locale_publication.yaml``.
2. The individual content item carries ``translation_status: published`` in its
   ``i18n.<locale>`` block (tools.yaml / blog.yaml), and is not marked
   ``noindex: true``.

Missing/legacy overrides are treated as quarantined. This is intentional: the
old presence-based check advertised thin machine-translated pages. Quarantined
pages remain reachable (HTTP 200, ``noindex, follow``) so users and internal
links keep working, but they are excluded from sitemaps, hreflang clusters and
robots.txt sitemap listings.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

import yaml

from app.core.config import settings
from app.core.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, normalize_locale, split_locale_path

PUBLISHED = "published"
QUARANTINED = "quarantined"
MISSING = "missing"

_VALID_STATUSES = frozenset({PUBLISHED, QUARANTINED, "draft", "review"})
_CONFIG_TTL = 300.0
_config_lock = threading.RLock()
_config_cache: tuple[float, dict[str, dict[str, Any]]] | None = None

# Static/legal pages that must never inherit a locale-wide "static" surface
# release: they currently serve the identical English body behind every locale.
# This hard safety net stays in place even if a path is added to the
# config-driven ``static_pages`` allowlist.
_STATIC_EN_ONLY = frozenset({"/about", "/contact", "/privacy", "/terms", "/disclaimer"})


@dataclass(frozen=True)
class LocaleDecision:
    """Why a localized URL is (not) indexable."""

    locale: str
    indexable: bool
    status: str
    reason: str = ""


def clear_cache() -> None:
    """Drop the publication config cache (tests + operational rollback)."""
    global _config_cache
    with _config_lock:
        _config_cache = None


def _config_path() -> str:
    return os.path.join(settings.base_dir, "data", "locale_publication.yaml")


def _normalize_static_path(value: Any) -> str:
    """Normalize a config static-page entry to a bare path (``/impressum``)."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    if "://" in raw or raw.startswith("//"):
        return ""
    if not raw.startswith("/"):
        raw = "/" + raw
    raw = raw.split("?", 1)[0].split("#", 1)[0]
    _, bare = split_locale_path(raw)
    if len(bare) > 1:
        bare = bare.rstrip("/")
    if bare == "/":
        return ""
    return bare.lower()


def _load_config() -> dict[str, dict[str, Any]]:
    """Load and normalize the release file. Fail closed on any error."""
    global _config_cache
    now = time.monotonic()
    with _config_lock:
        if _config_cache is not None and now - _config_cache[0] < _CONFIG_TTL:
            return _config_cache[1]

        try:
            with open(_config_path(), "rb") as f:
                raw = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError):
            raw = {}

        raw_locales = raw.get("locales") if isinstance(raw, dict) else None
        raw_locales = raw_locales if isinstance(raw_locales, dict) else {}

        normalized: dict[str, dict[str, Any]] = {}
        for code in SUPPORTED_LOCALES:
            if code == DEFAULT_LOCALE:
                # English is the origin locale and is never quarantined.
                normalized[code] = {"status": PUBLISHED, "surfaces": ["*"]}
                continue

            entry = raw_locales.get(code)
            if isinstance(entry, str):
                entry = {"status": entry}
            if not isinstance(entry, dict):
                entry = {}

            status = str(entry.get("status") or QUARANTINED).strip().lower()
            if status not in _VALID_STATUSES:
                status = QUARANTINED

            raw_surfaces = entry.get("surfaces")
            surfaces = (
                [str(item).strip().lower() for item in raw_surfaces if str(item).strip()]
                if isinstance(raw_surfaces, list)
                else []
            )
            raw_static = entry.get("static_pages")
            static_pages: list[str] = []
            if isinstance(raw_static, list):
                for item in raw_static:
                    bare = _normalize_static_path(item)
                    if bare and bare not in static_pages:
                        static_pages.append(bare)
            normalized[code] = {"status": status, "surfaces": surfaces, "static_pages": static_pages}

        _config_cache = (now, normalized)
        return normalized


def locale_status(locale: str) -> str:
    """Return ``published``/``quarantined`` for a locale code."""
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return PUBLISHED
    return str(_load_config()[loc]["status"])


def is_locale_released(locale: str) -> bool:
    """True when the locale itself is released for indexing."""
    return locale_status(locale) == PUBLISHED


def published_locales() -> list[str]:
    """Released locales in canonical order, always including English."""
    return [loc for loc in SUPPORTED_LOCALES if is_locale_released(loc)]


def _surfaces_for(locale: str) -> set[str]:
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return {"*"}
    return set(_load_config()[loc]["surfaces"])


def is_surface_indexable(locale: str, surface: str) -> bool:
    """True when a locale-wide surface (home/tools/blog/hubs/static) may index."""
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return True
    if not is_locale_released(loc):
        return False
    surfaces = _surfaces_for(loc)
    return "*" in surfaces or surface.strip().lower() in surfaces


def static_pages_for(locale: str) -> list[str]:
    """Static paths explicitly released for one locale (empty for English).

    A page must appear here *and* the locale must release the ``static``
    surface. This lets localized legal pages (Impressum / Aviso legal /
    Mentions légales) ship one at a time instead of flipping every static URL
    at once.
    """
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return []
    entry = _load_config()[loc]
    pages = entry.get("static_pages")
    if not isinstance(pages, list):
        return []
    normalized: list[str] = []
    for page in pages:
        bare = _normalize_static_path(page)
        if bare and bare not in normalized:
            normalized.append(bare)
    return normalized


def _static_page_allowed(locale: str, bare_path: str) -> bool:
    loc = normalize_locale(locale)
    bare_path = bare_path.strip().lower()
    if loc == DEFAULT_LOCALE:
        return True
    if not is_locale_released(loc):
        return False
    if bare_path in _STATIC_EN_ONLY or bare_path == "/sitemap":
        return False
    surfaces = _surfaces_for(loc)
    if "*" not in surfaces and "static" not in surfaces:
        return False
    return bare_path in static_pages_for(loc)


def _overrides_for(raw: Any) -> dict[str, Any]:
    i18n = raw.get("i18n") if isinstance(raw, dict) else None
    return i18n if isinstance(i18n, dict) else {}


def _has_translation_text(over: Any) -> bool:
    if not isinstance(over, dict) or not over:
        return False
    return bool(
        over.get("name")
        or over.get("title")
        or over.get("description")
        or over.get("body_html")
        or over.get("meta_title")
    )


def translation_decision(over: Any, locale: str) -> LocaleDecision:
    """Decide whether one localized content item is indexable."""
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return LocaleDecision(loc, True, PUBLISHED, "default_locale")
    if not is_locale_released(loc):
        return LocaleDecision(loc, False, QUARANTINED, "locale_not_released")
    if not _has_translation_text(over):
        return LocaleDecision(loc, False, MISSING, "no_translation")
    if not isinstance(over, dict):
        return LocaleDecision(loc, False, QUARANTINED, "invalid_override")
    if over.get("noindex") is True:
        return LocaleDecision(loc, False, QUARANTINED, "content_noindex")

    status = str(over.get("translation_status") or "").strip().lower()
    if status != PUBLISHED:
        return LocaleDecision(loc, False, status or QUARANTINED, "translation_not_published")
    return LocaleDecision(loc, True, PUBLISHED, "published")


def _locales_for_overrides(overrides: dict[str, Any]) -> list[str]:
    result: list[str] = [DEFAULT_LOCALE]
    for loc in SUPPORTED_LOCALES:
        if loc == DEFAULT_LOCALE:
            continue
        if translation_decision(overrides.get(loc), loc).indexable:
            result.append(loc)
    return result


def _tool_raw(slug: str) -> dict[str, Any]:
    try:
        from app.core.tool_data import ToolDataLoader  # noqa: PLC0415

        info = ToolDataLoader.get(slug)
    except Exception:
        return {}
    return info if isinstance(info, dict) else {}


def _blog_raw(slug: str) -> dict[str, Any]:
    try:
        from app.services.blog_service import BlogService  # noqa: PLC0415

        info = BlogService(settings)._load_raw().get(slug)
    except Exception:
        return {}
    return info if isinstance(info, dict) else {}


def tool_locales(slug: str) -> list[str]:
    """Indexable locales for one tool (EN always first when the slug exists)."""
    raw = _tool_raw(slug)
    if not raw:
        return []
    return _locales_for_overrides(_overrides_for(raw))


def blog_locales(slug: str) -> list[str]:
    """Indexable locales for one blog post."""
    raw = _blog_raw(slug)
    if not raw:
        return []
    return _locales_for_overrides(_overrides_for(raw))


def _surface_locales(surface: str) -> list[str]:
    return [loc for loc in SUPPORTED_LOCALES if is_surface_indexable(loc, surface)]


def path_surface(bare_path: str) -> str:
    """Map a bare path to its locale-wide surface key."""
    _, bare = split_locale_path(bare_path)
    if bare == "/":
        return "home"
    if bare == "/tools":
        return "tools"
    if bare == "/blog":
        return "blog"
    if bare.startswith("/blog/"):
        return "blog_pillars" if bare.count("/") == 2 else "static"
    if bare.strip("/") in settings.HUB_CATEGORIES:
        return "hubs"
    return "static"


def indexable_locales_for_path(bare_path: str) -> list[str]:
    """Locales that may appear in the hreflang cluster for a bare path.

    Only indexable URLs belong here. A quarantined localized URL must not be
    advertised as an alternate, even if the page returns 200.
    """
    _, bare = split_locale_path(bare_path)

    if bare.startswith("/tool/"):
        slug = bare[len("/tool/") :].split("/")[0]
        return tool_locales(slug) if slug else [DEFAULT_LOCALE]

    if bare.startswith("/blog/"):
        parts = bare.strip("/").split("/")
        if len(parts) == 3 and parts[0] == "blog":
            return blog_locales(parts[2]) or [DEFAULT_LOCALE]
        if len(parts) == 2 and parts[0] == "blog":
            return _surface_locales("blog_pillars")

    if bare == "/blog":
        return _surface_locales("blog")
    if bare == "/":
        return _surface_locales("home")
    if bare == "/tools":
        return _surface_locales("tools")
    if bare.strip("/") in settings.HUB_CATEGORIES:
        return _surface_locales("hubs")
    if bare == "/sitemap" or bare in _STATIC_EN_ONLY:
        return [DEFAULT_LOCALE]
    # Static pages are opt-in per path: a locale-wide ``static`` release alone
    # must not advertise legal pages that still render English content.
    return [DEFAULT_LOCALE] + [
        loc for loc in SUPPORTED_LOCALES if loc != DEFAULT_LOCALE and _static_page_allowed(loc, bare)
    ]


def is_path_indexable(locale: str, bare_path: str) -> bool:
    """True when a specific localized URL should be indexed."""
    loc = normalize_locale(locale)
    if loc == DEFAULT_LOCALE:
        return True
    if not is_locale_released(loc):
        return False
    _, bare = split_locale_path(bare_path)
    if bare in _STATIC_EN_ONLY:
        return False
    return loc in indexable_locales_for_path(bare)
