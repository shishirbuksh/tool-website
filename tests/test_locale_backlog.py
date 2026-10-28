"""Locale backlog tests: readiness classification, blockers, and report files."""

from __future__ import annotations

import csv
import json
from types import SimpleNamespace

import pytest

from scripts import locale_backlog


def _faq(index: int) -> dict[str, str]:
    return {
        "q": f"Wie berechnet der Kreditrechner Fall {index}?",
        "a": (
            "Der Kreditrechner zeigt die monatliche Rate, die Tilgung und die Zinsen für die gesamte Laufzeit "
            "und berücksichtigt dabei auch eine mögliche Sondertilgung."
        ),
    }


def _complete_de_tool(**overrides) -> dict:
    sentence = (
        "Der Kreditrechner zeigt die monatliche Rate, die Tilgung und die Zinsen für die Laufzeit. "
        "Die Berechnung berücksichtigt die Laufzeit und zeigt, wie sich Zinsen und Tilgung verändern. "
    )
    pack = {
        "name": "Kreditrechner",
        "meta_title": "Kreditrechner: Rate, Tilgung und Zinsen berechnen",
        "description": (
            "Mit dem Kreditrechner berechnen Sie monatliche Rate, Tilgung und Zinsen für Ihre Laufzeit. "
            "Vergleichen Sie Szenarien und planen Sie Ihre Finanzierung."
        ),
        "keywords": ["Kreditrechner", "Tilgung", "Zinsen", "Laufzeit"],
        "about_body": sentence * 6,
        "faqs": [_faq(index) for index in range(1, 6)],
        "translation_status": "review",
        "reviewer": "Native Reviewer DE",
        "reviewed_at": "2026-10-20",
        "author": "StoryBrain AI",
        "sources": ["https://www.bundesbank.de/"],
    }
    pack.update(overrides)
    return pack


def _row(over: dict | None, *, status: str | None = None, issues=None):
    raw = {"category": "Calculators"}
    if status is not None and over is not None:
        over = {**over, "translation_status": status}
    return locale_backlog._item_row(
        locale="de",
        kind="tool",
        slug="emi-calculator",
        raw=raw,
        over=over,
        issues=issues or [],
        released={"en"},
    )


class TestLocaleSelection:
    def test_defaults_to_rollout_order(self):
        assert locale_backlog._selected_locales([]) == ["de", "es", "fr", "hi"]

    def test_rejects_english(self):
        with pytest.raises(ValueError, match="non-English"):
            locale_backlog._selected_locales(["en"])

    def test_rejects_unknown(self):
        with pytest.raises(ValueError, match="unknown locale"):
            locale_backlog._selected_locales(["xx"])


class TestArtifacts:
    def test_hard_artifact_in_body_is_blocking(self):
        assert locale_backlog._artifact_codes({"body_html": "<p>LSI: Kredit, Zins</p>"}) == ["lsi_scaffold"]

    def test_todo_in_code_sample_is_not_blocking(self):
        assert locale_backlog._artifact_codes({"body_html": "<pre>TODO: later</pre>"}) == []

    def test_todo_in_prose_is_blocking(self):
        assert locale_backlog._artifact_codes({"description": "TODO: later"}) == ["todo_marker"]


class TestReadiness:
    def test_missing_override_is_missing(self):
        item = _row(None)
        assert item.readiness == "missing"
        assert item.blockers == ("missing_translation",)
        assert "translation_status" in item.missing_fields

    def test_thin_legacy_override_is_blocked(self):
        over = _complete_de_tool(about_body="Kreditrechner mit LSI: Rate und Zinsen.", faqs=[_faq(1)])
        for key in ("translation_status", "reviewer", "reviewed_at", "author", "sources"):
            over.pop(key)
        item = _row(over)
        assert item.readiness == "blocked"
        assert {"tool_about_too_thin", "tool_faq_count", "lsi_scaffold"} <= set(item.blockers)
        assert {"translation_status", "reviewer", "reviewed_at", "author", "sources"} <= set(item.missing_fields)

    def test_empty_body_is_blocked(self):
        item = _row(_complete_de_tool(about_body=""))
        assert "missing_body" in item.blockers
        assert "tool_about_too_thin" in item.blockers
        assert "about_body" in item.missing_fields

    def test_complete_pack_waits_for_review(self):
        item = _row(_complete_de_tool())
        assert item.blockers == ()
        assert item.readiness == "review"
        assert item.word_count >= item.word_min
        assert item.faq_count >= item.faq_min

    def test_published_pack_in_quarantined_locale_is_ready_not_released(self, monkeypatch):
        monkeypatch.setattr(locale_backlog, "translation_decision", lambda over, loc: SimpleNamespace(indexable=False))
        item = _row(_complete_de_tool(), status="published")
        assert item.blockers == ()
        assert item.indexable is False
        assert item.readiness == "ready"

    def test_released_pack_is_released(self, monkeypatch):
        monkeypatch.setattr(locale_backlog, "translation_decision", lambda over, loc: SimpleNamespace(indexable=True))
        item = _row(_complete_de_tool(), status="published")
        assert item.readiness == "released"

    def test_published_but_thin_pack_stays_blocked(self, monkeypatch):
        monkeypatch.setattr(locale_backlog, "translation_decision", lambda over, loc: SimpleNamespace(indexable=True))
        item = _row(_complete_de_tool(about_body="Zu dünn."), status="published")
        assert item.indexable is True
        assert item.readiness == "blocked"


class TestReportFiles:
    def test_csv_and_json_are_written(self, tmp_path):
        report = locale_backlog.BacklogReport(
            locales=["de"],
            items=[_row(_complete_de_tool()), _row(None)],
        )
        csv_path = tmp_path / "backlog.csv"
        json_path = tmp_path / "backlog.json"
        locale_backlog.write_csv(csv_path, report)
        locale_backlog.write_json(json_path, report)

        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 2
        assert rows[0]["locale"] == "de"
        assert rows[0]["readiness"] == "review"
        assert rows[1]["readiness"] == "missing"
        assert rows[0]["blockers"] == ""

        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == locale_backlog.SCHEMA_VERSION
        assert data["totals"]["items"] == 2
        assert data["totals"]["by_readiness"] == {"missing": 1, "review": 1}
        assert data["items"][0]["path"] == "/de/tool/emi-calculator"


class TestGateIntegration:
    def test_build_backlog_reads_gate_issues(self):
        report = locale_backlog.build_backlog(["de"], kinds={"tool"}, slugs={"ad-performance-analyzer"})
        assert len(report.items) == 1
        item = report.items[0]
        assert item.slug == "ad-performance-analyzer"
        assert item.readiness == "blocked"
        assert "lsi_scaffold" in item.blockers
        assert "translation_status_missing" in item.blockers

    def test_rebuilt_de_emi_is_blocked_only_on_native_review(self):
        report = locale_backlog.build_backlog(["de"], kinds={"tool"}, slugs={"emi-calculator"})
        assert len(report.items) == 1
        item = report.items[0]
        assert item.readiness == "blocked"
        assert item.blockers == ("missing_reviewed_at", "missing_reviewer")
        assert "lsi_scaffold" not in item.blockers
        assert item.word_count >= 150
        assert item.faq_count >= 5
