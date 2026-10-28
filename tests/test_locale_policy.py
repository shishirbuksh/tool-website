"""Locale publication policy tests: two-gate indexability and fail-closed defaults."""

from __future__ import annotations

import pytest

from app.core import locale_policy
from app.core.content_sanitize import clean_localized_text, clean_localized_value
from app.core.i18n import SUPPORTED_LOCALES


def _config(
    *,
    released: set[str],
    surfaces: dict[str, list[str]] | None = None,
    static_pages: dict[str, list[str]] | None = None,
) -> dict:
    surfaces = surfaces or {}
    static_pages = static_pages or {}
    result = {}
    for loc in SUPPORTED_LOCALES:
        if loc == "en":
            result[loc] = {"status": "published", "surfaces": ["*"], "static_pages": []}
        elif loc in released:
            result[loc] = {
                "status": "published",
                "surfaces": surfaces.get(loc, []),
                "static_pages": static_pages.get(loc, []),
            }
        else:
            result[loc] = {"status": "quarantined", "surfaces": [], "static_pages": []}
    return result


class TestLocaleRelease:
    def test_default_quarantines_all_non_en(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "_load_config", lambda: _config(released=set()))
        assert locale_policy.published_locales() == ["en"]
        for loc in ("hi", "es", "fr", "de"):
            assert locale_policy.is_locale_released(loc) is False
            assert locale_policy.is_surface_indexable(loc, "home") is False

    def test_released_locale_surfaces_are_explicit(self, monkeypatch):
        monkeypatch.setattr(
            locale_policy,
            "_load_config",
            lambda: _config(released={"de"}, surfaces={"de": ["home", "blog"]}),
        )
        assert locale_policy.is_locale_released("de") is True
        assert locale_policy.is_surface_indexable("de", "home") is True
        assert locale_policy.is_surface_indexable("de", "blog") is True
        assert locale_policy.is_surface_indexable("de", "tools") is False
        assert locale_policy.is_surface_indexable("de", "static") is False
        # English is always fully indexable.
        assert locale_policy.is_surface_indexable("en", "anything") is True


class TestTranslationGate:
    def test_missing_translation_is_not_indexable(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "_load_config", lambda: _config(released={"de"}))
        decision = locale_policy.translation_decision(None, "de")
        assert decision.indexable is False
        assert decision.reason == "no_translation"

    def test_locale_gate_precedes_item_status(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "_load_config", lambda: _config(released=set()))
        decision = locale_policy.translation_decision(
            {"name": "Rechner", "translation_status": "published"}, "de"
        )
        assert decision.indexable is False
        assert decision.reason == "locale_not_released"

    def test_item_requires_published_status(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "_load_config", lambda: _config(released={"de"}))
        under_review = locale_policy.translation_decision({"name": "Rechner"}, "de")
        assert under_review.indexable is False
        assert under_review.reason == "translation_not_published"

        draft = locale_policy.translation_decision(
            {"name": "Rechner", "translation_status": "draft"}, "de"
        )
        assert draft.indexable is False

        published = locale_policy.translation_decision(
            {"name": "Rechner", "translation_status": "published"}, "de"
        )
        assert published.indexable is True

    def test_content_noindex_override_wins(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "_load_config", lambda: _config(released={"de"}))
        decision = locale_policy.translation_decision(
            {"name": "Rechner", "translation_status": "published", "noindex": True}, "de"
        )
        assert decision.indexable is False
        assert decision.reason == "content_noindex"


class TestPathClusters:
    def test_tool_and_blog_clusters_use_item_decisions(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "tool_locales", lambda slug: ["en", "de"])
        monkeypatch.setattr(locale_policy, "blog_locales", lambda slug: ["en", "es"])
        assert locale_policy.indexable_locales_for_path("/tool/emi-calculator") == ["en", "de"]
        assert locale_policy.indexable_locales_for_path("/blog/calculators/emi-guide") == ["en", "es"]

    def test_surfaces_and_static_pages(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "_load_config", lambda: _config(released={"de"}))
        assert locale_policy.indexable_locales_for_path("/") == ["en"]
        assert locale_policy.indexable_locales_for_path("/blog") == ["en"]
        monkeypatch.setattr(
            locale_policy,
            "_load_config",
            lambda: _config(released={"de"}, surfaces={"de": ["home", "blog"]}),
        )
        assert locale_policy.indexable_locales_for_path("/") == ["en", "de"]
        assert locale_policy.indexable_locales_for_path("/blog") == ["en", "de"]
        # Legal pages never inherit a locale-wide static release.
        assert locale_policy.indexable_locales_for_path("/contact") == ["en"]
        assert locale_policy.is_path_indexable("de", "/contact") is False

    def test_static_pages_require_per_page_allowlist(self, monkeypatch):
        # A `static` surface release alone does not advertise static pages.
        monkeypatch.setattr(
            locale_policy,
            "_load_config",
            lambda: _config(released={"de"}, surfaces={"de": ["static"]}),
        )
        assert locale_policy.indexable_locales_for_path("/impressum") == ["en"]
        assert locale_policy.is_path_indexable("de", "/impressum") is False
        assert locale_policy.static_pages_for("de") == []

        # Explicit per-page allowlist (locale prefix + trailing slash normalized).
        monkeypatch.setattr(
            locale_policy,
            "_load_config",
            lambda: _config(
                released={"de"},
                surfaces={"de": ["static"]},
                static_pages={"de": ["/de/", "/de/impressum/"]},
            ),
        )
        assert locale_policy.static_pages_for("de") == ["/impressum"]
        assert locale_policy.indexable_locales_for_path("/impressum") == ["en", "de"]
        assert locale_policy.is_path_indexable("de", "/de/impressum") is True

    def test_static_page_allowlist_needs_static_surface(self, monkeypatch):
        monkeypatch.setattr(
            locale_policy,
            "_load_config",
            lambda: _config(
                released={"de"},
                surfaces={"de": ["home"]},
                static_pages={"de": ["/impressum"]},
            ),
        )
        assert locale_policy.indexable_locales_for_path("/impressum") == ["en"]
        assert locale_policy.is_path_indexable("de", "/impressum") is False

    def test_english_fallback_pages_stay_blocked_even_if_allowlisted(self, monkeypatch):
        monkeypatch.setattr(
            locale_policy,
            "_load_config",
            lambda: _config(
                released={"de"},
                surfaces={"de": ["static"]},
                static_pages={"de": ["/privacy", "/terms", "/about"]},
            ),
        )
        for bare in ("/privacy", "/terms", "/about"):
            assert locale_policy.indexable_locales_for_path(bare) == ["en"]
            assert locale_policy.is_path_indexable("de", bare) is False

    def test_missing_item_returns_no_locales(self, monkeypatch):
        monkeypatch.setattr(locale_policy, "tool_locales", lambda slug: [])
        assert locale_policy.indexable_locales_for_path("/tool/unknown") == []


class TestContentSanitizer:
    def test_removes_lsi_block(self):
        value = '<p>Useful copy.</p><p>LSI: precision, speed, privacy.</p>'
        assert clean_localized_text(value) == "<p>Useful copy.</p>"

    def test_removes_inline_lsi(self):
        assert clean_localized_text("Resultado. LSI: precisión, velocidad.") == "Resultado."

    def test_recurses_into_overrides(self):
        cleaned = clean_localized_value({"about_body": "<p>LSI: junk.</p>", "faqs": [{"q": "LSI: x."}]})
        assert cleaned == {"about_body": "", "faqs": [{"q": ""}]}

    def test_leaves_clean_text_untouched(self):
        assert clean_localized_text("Texto limpio.") == "Texto limpio."


@pytest.mark.parametrize("loc", ["hi", "es", "fr", "de"])
def test_quarantined_locale_never_has_positive_decision(loc, monkeypatch):
    monkeypatch.setattr(locale_policy, "_load_config", lambda: _config(released=set()))
    assert locale_policy.translation_decision({"name": "x", "translation_status": "published"}, loc).indexable is False
