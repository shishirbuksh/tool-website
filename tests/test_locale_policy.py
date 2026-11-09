"""Locale publication policy tests: English-only single source of truth."""

from __future__ import annotations

import pytest

from app.core import locale_policy
from app.core.content_sanitize import clean_localized_text, clean_localized_value


class TestLocaleRelease:
    def test_default_quarantines_all_non_en(self):
        assert locale_policy.published_locales() == ["en"]
        assert locale_policy.is_locale_released("en") is True
        for loc in ("hi", "es", "fr", "de", "zh", "ja"):
            assert locale_policy.is_locale_released(loc) is False
            assert locale_policy.is_surface_indexable(loc, "home") is False
            assert locale_policy.is_surface_indexable(loc, "tools") is False
            assert locale_policy.is_surface_indexable(loc, "blog") is False

    def test_english_surfaces_are_indexable(self):
        assert locale_policy.is_locale_released("en") is True
        assert locale_policy.is_surface_indexable("en", "home") is True
        assert locale_policy.is_surface_indexable("en", "tools") is True
        assert locale_policy.is_surface_indexable("en", "blog") is True
        assert locale_policy.is_surface_indexable("en", "anything") is True


class TestTranslationGate:
    def test_english_is_published(self):
        decision = locale_policy.translation_decision(None, "en")
        assert decision.indexable is True
        assert decision.status == locale_policy.PUBLISHED

    def test_non_en_is_quarantined(self):
        for loc in ("hi", "es", "fr", "de", "xx"):
            decision = locale_policy.translation_decision({"name": "Rechner"}, loc)
            assert decision.indexable is False
            assert decision.status == locale_policy.QUARANTINED
            assert decision.reason == "non_english_unsupported"


class TestPathClusters:
    def test_tool_and_blog_clusters(self):
        assert locale_policy.tool_locales("emi-calculator") == ["en"]
        assert locale_policy.blog_locales("emi-calculator-guide") == ["en"]
        assert locale_policy.indexable_locales_for_path("/tool/emi-calculator") == ["en"]
        assert locale_policy.indexable_locales_for_path("/blog/calculators/emi-guide") == ["en"]

    def test_surfaces_and_paths(self):
        assert locale_policy.indexable_locales_for_path("/") == ["en"]
        assert locale_policy.indexable_locales_for_path("/blog") == ["en"]
        assert locale_policy.indexable_locales_for_path("/tools") == ["en"]
        assert locale_policy.indexable_locales_for_path("/contact") == ["en"]

        assert locale_policy.is_path_indexable("en", "/") is True
        assert locale_policy.is_path_indexable("en", "/contact") is True
        assert locale_policy.is_path_indexable("de", "/") is False
        assert locale_policy.is_path_indexable("de", "/contact") is False


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


@pytest.mark.parametrize("loc", ["hi", "es", "fr", "de", "ja", "ru"])
def test_quarantined_locale_never_has_positive_decision(loc):
    assert locale_policy.translation_decision({"name": "x", "translation_status": "published"}, loc).indexable is False
