"""Locale release policy: English-only single source of truth for indexability.
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.i18n import DEFAULT_LOCALE, SUPPORTED_LOCALES, normalize_locale, split_locale_path

PUBLISHED = "published"
QUARANTINED = "quarantined"
MISSING = "missing"

INDIA_ONLY_TOOL_SLUGS = frozenset(
    {
        "gst-calculator",
        "eway-bill-calculator",
        "sip-calculator",
        "fd-calculator",
        "job-card-generator",
        "delivery-challan-generator",
    }
)
WESTERN_LOCALES = frozenset({"de", "es", "fr"})

_VALID_STATUSES = frozenset({PUBLISHED, QUARANTINED, "draft", "review"})
_STATIC_EN_ONLY = frozenset({"/about", "/contact", "/privacy", "/terms", "/disclaimer"})


@dataclass(frozen=True)
class LocaleDecision:
    """Why a localized URL is (not) indexable."""

    locale: str
    indexable: bool
    status: str
    reason: str = ""


def clear_cache() -> None:
    pass


def locale_status(locale: str) -> str:
    raw = (locale or "").strip().lower()
    return PUBLISHED if raw == DEFAULT_LOCALE else QUARANTINED


def is_locale_released(locale: str) -> bool:
    return bool(locale and locale.strip().lower() == DEFAULT_LOCALE)


def published_locales() -> list[str]:
    return [DEFAULT_LOCALE]


def is_surface_indexable(locale: str, surface: str) -> bool:
    return bool(locale and locale.strip().lower() == DEFAULT_LOCALE)


def static_pages_for(locale: str) -> list[str]:
    return []


def translation_decision(over: Any, locale: str) -> LocaleDecision:
    raw = (locale or "").strip().lower()
    if raw == DEFAULT_LOCALE:
        return LocaleDecision(DEFAULT_LOCALE, True, PUBLISHED, "default_locale")
    return LocaleDecision(raw or "unknown", False, QUARANTINED, "non_english_unsupported")


def tool_locales(slug: str) -> list[str]:
    return [DEFAULT_LOCALE]


def blog_locales(slug: str) -> list[str]:
    return [DEFAULT_LOCALE]


def path_surface(bare_path: str) -> str:
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
    return [DEFAULT_LOCALE]


def is_path_indexable(locale: str, bare_path: str) -> bool:
    return bool(locale and locale.strip().lower() == DEFAULT_LOCALE)
