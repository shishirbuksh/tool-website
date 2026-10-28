"""Quality-gate tests: localized depth, artifacts, provenance, and sitemap policy."""

from __future__ import annotations

from scripts.quality_gate import QualityGate, find_artifacts


def _faq(index: int) -> dict[str, str]:
    return {
        "q": f"Wie funktioniert der Kreditrechner im Fall {index}?",
        "a": (
            "Der Kreditrechner zeigt die monatliche Rate, die Tilgung und die Zinsen für die gesamte Laufzeit "
            "und berücksichtigt dabei auch eine mögliche Sondertilgung."
        ),
    }


def _valid_de_blog() -> dict:
    section = (
        "<h2>Kreditrechner und Tilgung</h2>"
        "<p>Der Kreditrechner zeigt die monatliche Rate, die Tilgung und die Zinsen für die Laufzeit. "
        "Die Berechnung berücksichtigt die Laufzeit und zeigt, wie sich Zinsen und Tilgung verändern. "
        '<a href="/de/tool/emi-calculator">Kreditrechner öffnen</a></p>'
        "<p>Der Kreditrechner zeigt die monatliche Rate, die Tilgung und die Zinsen für die Laufzeit. "
        "Die Berechnung berücksichtigt die Laufzeit und zeigt, wie sich Zinsen und Tilgung verändern. "
        "So lässt sich die monatliche Belastung besser planen.</p>"
    )
    body = "".join(section for _ in range(12))
    return {
        "title": "Kreditrechner: Rate, Tilgung und Zinsen berechnen",
        "meta_title": "Kreditrechner: Rate, Tilgung und Zinsen berechnen",
        "description": (
            "Mit dem Kreditrechner berechnen Sie monatliche Rate, Tilgung und Zinsen für Ihre Laufzeit. "
            "Vergleichen Sie Szenarien und planen Sie Ihre Finanzierung."
        ),
        "keywords": ["Kreditrechner", "Tilgung", "Zinsen", "Laufzeit"],
        "body_html": body,
        "faqs": [_faq(index) for index in range(1, 7)],
        "translation_status": "published",
        "reviewer": "Native Reviewer DE",
        "reviewed_at": "2026-10-20",
        "sources": ["https://www.bundesbank.de/"],
        "author": "StoryBrain AI",
    }


def _gate(locales: list[str] | None = None) -> QualityGate:
    return QualityGate(locales=locales or ["de"], check_sitemaps=False)


def _codes(gate: QualityGate) -> set[str]:
    return {issue.code for issue in gate.report.issues}


class TestArtifacts:
    def test_detects_replacement_char_and_lsi(self):
        codes = find_artifacts({"body": "Kredit \ufffd Rechner. LSI: präzision, tempo."})
        assert {"replacement_char", "lsi_scaffold"} <= set(codes)

    def test_does_not_flag_legitimate_todo_list(self):
        assert "todo_marker" not in find_artifacts({"title": "Die beste Todo Liste für Projekte"})

    def test_detects_code_style_marker(self):
        assert "todo_marker" in find_artifacts({"description": "TODO: Übersetzung fehlt"})


class TestLocalizedPack:
    def test_clean_pack_passes(self):
        gate = _gate()
        over = _valid_de_blog()
        gate._check_blog("de", "kreditrechner-guide", {"pillar": "finanzen", "body_html": "<p>Source</p>"}, over)
        assert gate.report.errors == [], [issue.message for issue in gate.report.errors]

    def test_thin_pack_fails_depth_checks(self):
        gate = _gate()
        over = _valid_de_blog()
        over["body_html"] = "<p>Der Kreditrechner ist zu dünn.</p>"
        over["faqs"] = []
        gate._check_blog("de", "kreditrechner-guide", {"pillar": "finanzen"}, over)
        codes = _codes(gate)
        assert {"blog_body_too_thin", "blog_h2_count", "blog_internal_links", "blog_faq_count"} <= codes

    def test_artifacts_and_missing_provenance_fail(self):
        gate = _gate()
        over = _valid_de_blog()
        over["meta_title"] = "Kreditrechner \ufffd"
        over["faqs"][0]["a"] = "LSI: Präzision, Tempo."
        for key in ("reviewer", "reviewed_at", "sources", "author"):
            over.pop(key)
        gate._check_blog("de", "kreditrechner-guide", {"pillar": "finanzen"}, over)
        codes = _codes(gate)
        assert {"replacement_char", "lsi_scaffold", "missing_reviewer", "missing_reviewed_at"} <= codes
        assert "missing_sources" in codes

    def test_english_body_in_german_pack_is_flagged(self):
        gate = _gate()
        english = "The credit calculator shows the monthly payment and the interest for the whole term. " * 30
        gate._check_language_signal("de", "tool", "credit-calculator", english)
        assert "likely_english" in _codes(gate)

    def test_native_german_body_is_not_flagged(self):
        gate = _gate()
        german = "Der Kreditrechner zeigt die monatliche Rate und die Tilgung für die Laufzeit. " * 30
        gate._check_language_signal("de", "tool", "kreditrechner", german)
        assert "likely_english" not in _codes(gate)


class TestStatusGate:
    def test_released_locale_rejects_unpublished_item(self):
        gate = _gate()
        gate.released = {"en", "de"}
        gate.statuses = {"review", "published"}
        assert gate._translation_selected("de", "tool", "x", {"translation_status": "review"}) is True
        assert "released_locale_unpublished_item" in _codes(gate)

    def test_missing_status_is_skipped_when_only_published_requested(self):
        gate = _gate()
        gate.released = {"en"}
        gate.statuses = {"published"}
        assert gate._translation_selected("de", "tool", "x", {}) is False
        assert "translation_status_missing" not in _codes(gate)

    def test_missing_status_warns_for_review_audit(self):
        gate = _gate()
        gate.released = {"en"}
        gate.statuses = {"review"}
        assert gate._translation_selected("de", "tool", "x", {}) is True
        assert "translation_status_missing" in _codes(gate)

    def test_invalid_status_is_rejected(self):
        gate = _gate()
        assert gate._translation_selected("de", "tool", "x", {"translation_status": "ready"}) is False
        assert "invalid_translation_status" in _codes(gate)

    def test_published_item_with_noindex_is_flagged(self):
        gate = _gate()
        gate.statuses = {"published"}
        assert gate._translation_selected("de", "tool", "x", {"translation_status": "published", "noindex": True}) is True
        assert "published_item_noindex" in _codes(gate)


class TestStaticPageSitemap:
    def test_released_static_page_must_be_listed(self, monkeypatch):
        gate = _gate()
        monkeypatch.setattr("scripts.quality_gate.static_pages_for", lambda loc: ["/impressum"])
        monkeypatch.setattr("scripts.quality_gate.is_path_indexable", lambda loc, bare: True)
        gate._check_surface_sitemap("de", set())
        assert "released_static_page_missing_from_sitemap" in _codes(gate)

    def test_listed_static_page_passes(self, monkeypatch):
        gate = _gate()
        monkeypatch.setattr("scripts.quality_gate.static_pages_for", lambda loc: ["/impressum"])
        monkeypatch.setattr("scripts.quality_gate.is_path_indexable", lambda loc, bare: True)
        gate._check_surface_sitemap("de", {"/impressum"})
        assert gate.report.errors == []

    def test_allowlisted_but_blocked_static_page_is_flagged(self, monkeypatch):
        gate = _gate()
        monkeypatch.setattr("scripts.quality_gate.static_pages_for", lambda loc: ["/privacy"])
        monkeypatch.setattr("scripts.quality_gate.is_path_indexable", lambda loc, bare: False)
        gate._check_surface_sitemap("de", {"/privacy"})
        assert "released_static_page_not_indexable" in _codes(gate)


class TestIndiaOnlyGuard:
    def test_india_only_tool_cannot_publish_for_de(self):
        gate = _gate()
        gate.statuses = {"published"}
        gate._translation_selected("de", "tool", "gst-calculator", {"translation_status": "published"})
        assert "india_only_tool_localized" in _codes(gate)

    def test_india_only_tool_is_allowed_for_hi(self):
        gate = _gate(locales=["hi"])
        gate.statuses = {"published"}
        gate._translation_selected("hi", "tool", "gst-calculator", {"translation_status": "published"})
        assert "india_only_tool_localized" not in _codes(gate)

    def test_india_only_tool_draft_is_not_flagged(self):
        gate = _gate()
        gate._translation_selected("de", "tool", "gst-calculator", {"translation_status": "draft"})
        assert "india_only_tool_localized" not in _codes(gate)


class TestRepositoryBaseline:
    def test_english_gate_passes_with_sitemap_consistency(self):
        gate = QualityGate(locales=["en"], check_sitemaps=True)
        report = gate.run()
        assert report.passed, [issue.message for issue in report.errors[:10]]
        assert report.items_checked == 216

    def test_quarantined_german_sample_is_blocked(self):
        gate = QualityGate(locales=["de"], slugs={"ad-performance-analyzer"}, check_sitemaps=False)
        report = gate.run()
        assert not report.passed
        codes = {issue.code for issue in report.errors}
        assert {"tool_about_too_thin", "tool_faq_count", "lsi_scaffold"} <= codes

    def test_rebuilt_german_emi_has_no_content_errors(self):
        gate = QualityGate(locales=["de"], slugs={"emi-calculator"}, check_sitemaps=False)
        report = gate.run()
        assert report.passed, [issue.message for issue in report.errors[:10]]
        codes = {issue.code for issue in report.warnings}
        assert {"missing_reviewer", "missing_reviewed_at"} <= codes
        assert not {"tool_about_too_thin", "tool_faq_count", "lsi_scaffold"} & codes


class TestPackSelection:
    def test_pack_infers_locale_and_slugs(self):
        from scripts.quality_gate import _pack_selection

        slugs, locales = _pack_selection(["data/content_packs/de_wave1a.yaml"])
        assert locales == {"de"}
        assert slugs == {
            "emi-calculator",
            "loan-affordability-calculator",
            "mortgage-overpayment-calculator",
            "debt-calculator",
            "compound-interest-formula",
        }

    def test_pack_parser_accepts_repeated_pack_flags(self):
        from scripts.quality_gate import build_parser

        args = build_parser().parse_args(["--pack", "a.yaml", "--pack", "b.yaml"])
        assert args.packs == ["a.yaml", "b.yaml"]
