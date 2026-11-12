"""Quality-gate tests for English SEO metadata, artifacts, and sitemap consistency."""

from __future__ import annotations

from scripts.quality_gate import QualityGate, build_parser, find_artifacts, main


class TestArtifactScanner:
    def test_detects_replacement_char_and_lsi(self):
        assert "replacement_char" in find_artifacts("bad \ufffd char")
        assert "lsi_scaffold" in find_artifacts("Includes LSI: debt snowball.")

    def test_does_not_flag_legitimate_todo_list(self):
        assert "todo_marker" not in find_artifacts("Use this TODO list app daily.")

    def test_detects_todo_marker(self):
        assert "todo_marker" in find_artifacts("TODO: add intro paragraph later")


class TestEnglishQualityGate:
    def test_english_gate_passes_with_sitemap_consistency(self):
        gate = QualityGate(locales=["en"], check_sitemaps=True)
        report = gate.run()
        assert report.errors == [], f"Unexpected errors: {[e.to_dict() for e in report.errors]}"
        assert report.items_checked > 200

    def test_cli_single_slug_dry(self):
        parser = build_parser()
        args = parser.parse_args(["--slug", "emi-calculator", "--no-sitemap"])
        assert args.slugs == ["emi-calculator"]
        assert args.no_sitemap is True
        rc = main(["--slug", "emi-calculator", "--no-sitemap", "--quiet"])
        assert rc == 0
