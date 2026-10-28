"""Surgical content-pack applier tests: target isolation, CRLF, and validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts import apply_content_pack as applier


def _tool_override(**overrides):
    pack = {
        "name": "Kreditrechner",
        "meta_title": "Kreditrechner: Rate, Zinsen und Tilgung berechnen",
        "description": (
            "Mit dem Kreditrechner berechnen Sie Monatsrate, Zinsen und Tilgung für Ihre Laufzeit. "
            "Vergleichen Sie Szenarien und planen Sie die Finanzierung."
        ),
        "keywords": ["Kreditrechner", "Monatsrate", "Zinsen", "Tilgung"],
        "faqs": [
            {
                "q": f"Wie funktioniert der Kreditrechner in Fall {index}?",
                "a": (
                    "Der Kreditrechner zeigt die Monatsrate, die Zinsen und die Tilgung für die gesamte "
                    "Laufzeit und berücksichtigt auch eine mögliche Sondertilgung."
                ),
            }
            for index in range(1, 6)
        ],
        "howto_steps": [{"title": "Daten eingeben", "desc": "Geben Sie Kreditsumme, Zins und Laufzeit ein."}],
        "howto_calculate": "Die Monatsrate wird aus Kreditsumme, Zins und Laufzeit berechnet.",
        "about_title": "Über den Kreditrechner",
        "about_body": "<p>Der Kreditrechner ist ein kostenloses Werkzeug für die Kreditplanung.</p>",
        "translation_status": "review",
        "author": "StoryBrain AI",
        "sources": ["https://www.bundesbank.de/de"],
    }
    pack.update(overrides)
    return pack


def _fixture() -> str:
    return (
        "tools:\n"
        "  alpha:\n"
        "    name: Alpha\n"
        "    i18n:\n"
        "      de:\n"
        "        name: Alpha DE\n"
        "        meta_title: Alpha DE Titel\n"
        "      es:\n"
        "        name: Alpha ES\n"
        "  beta:\n"
        "    name: Beta\n"
        "    i18n:\n"
        "      de:\n"
        "        name: Beta DE\n"
        "posts:\n"
        "  guide:\n"
        "    title: Guide\n"
    )


class TestReplaceOverride:
    def test_replaces_only_target_locale(self):
        text = _fixture()
        override = _tool_override()
        result = applier.replace_override(text, kind="tool", slug="alpha", locale="de", override=override)
        data = yaml.safe_load(result)
        assert data["tools"]["alpha"]["i18n"]["de"] == override
        assert data["tools"]["alpha"]["i18n"]["es"] == {"name": "Alpha ES"}
        assert data["tools"]["beta"] == yaml.safe_load(text)["tools"]["beta"]
        assert data["posts"] == yaml.safe_load(text)["posts"]

    def test_inserts_missing_locale(self):
        text = _fixture()
        override = _tool_override()
        result = applier.replace_override(text, kind="tool", slug="beta", locale="es", override=override)
        data = yaml.safe_load(result)
        assert data["tools"]["beta"]["i18n"]["de"] == {"name": "Beta DE"}
        assert data["tools"]["beta"]["i18n"]["es"] == override

    def test_missing_slug_is_rejected(self):
        with pytest.raises(applier.PackError, match="not found"):
            applier.replace_override(_fixture(), kind="tool", slug="missing", locale="de", override=_tool_override())

    def test_missing_section_is_rejected(self):
        with pytest.raises(applier.PackError, match="section not found"):
            applier.replace_override("posts:\n  guide:\n    title: Guide\n", kind="tool", slug="alpha", locale="de", override=_tool_override())


class TestApplyPack:
    def _write_fixture(self, tmp_path: Path) -> Path:
        path = tmp_path / "tools.yaml"
        path.write_bytes(_fixture().replace("\n", "\r\n").encode("utf-8"))
        return path

    def test_dry_run_does_not_write(self, tmp_path, monkeypatch):
        path = self._write_fixture(tmp_path)
        before = path.read_bytes()
        monkeypatch.setitem(applier.CONTENT_FILES, "tool", path)
        pack = applier.Pack(locale="de", tools={"alpha": _tool_override()}, posts={})
        changes = applier.apply_pack(pack)
        assert changes == [applier.Change("tool", "alpha", path, True)]
        assert path.read_bytes() == before

    def test_write_preserves_crlf_and_other_content(self, tmp_path, monkeypatch):
        path = self._write_fixture(tmp_path)
        monkeypatch.setitem(applier.CONTENT_FILES, "tool", path)
        pack = applier.Pack(locale="de", tools={"alpha": _tool_override()}, posts={})
        applier.apply_pack(pack, write=True)
        raw = path.read_bytes()
        assert raw.count(b"\r\n") == raw.count(b"\n")
        data = yaml.safe_load(raw.decode("utf-8"))
        assert data["tools"]["alpha"]["i18n"]["de"] == _tool_override()
        assert data["tools"]["beta"] == yaml.safe_load(_fixture())["tools"]["beta"]

    def test_published_requires_explicit_flag(self, tmp_path, monkeypatch):
        path = self._write_fixture(tmp_path)
        monkeypatch.setitem(applier.CONTENT_FILES, "tool", path)
        override = _tool_override(translation_status="published")
        pack = applier.Pack(locale="de", tools={"alpha": override}, posts={})
        with pytest.raises(applier.PackError, match="published"):
            applier.apply_pack(pack, write=True)

    def test_verify_rejects_unrelated_change(self):
        old = {"tools": {"alpha": {"name": "A", "i18n": {"de": {"name": "A DE"}}}, "beta": {"name": "B"}}}
        new = {
            "tools": {
                "alpha": {"name": "A", "i18n": {"de": _tool_override()}},
                "beta": {"name": "B changed"},
            }
        }
        with pytest.raises(applier.PackError, match="unrelated item"):
            applier._verify_merge(old, new, kind="tool", slug="alpha", locale="de", override=_tool_override())


class TestPackValidation:
    def _write_pack(self, tmp_path: Path, payload: dict) -> Path:
        path = tmp_path / "pack.yaml"
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def test_loads_valid_pack(self, tmp_path):
        path = self._write_pack(
            tmp_path,
            {"locale": "de", "wave": "1a", "tools": {"alpha": _tool_override()}, "posts": {}},
        )
        pack = applier.load_pack(path)
        assert pack.locale == "de"
        assert pack.wave == "1a"
        assert pack.tools["alpha"]["name"] == "Kreditrechner"

    def test_rejects_unknown_locale(self, tmp_path):
        path = self._write_pack(tmp_path, {"locale": "en", "tools": {"alpha": _tool_override()}})
        with pytest.raises(applier.PackError, match="locale"):
            applier.load_pack(path)

    def test_rejects_unknown_field(self, tmp_path):
        override = _tool_override()
        override["h1"] = "Kreditrechner"
        path = self._write_pack(tmp_path, {"locale": "de", "tools": {"alpha": override}})
        with pytest.raises(applier.PackError, match="unsupported field"):
            applier.load_pack(path)

    def test_rejects_short_faq_list(self, tmp_path):
        override = _tool_override(faqs=_tool_override()["faqs"][:3])
        path = self._write_pack(tmp_path, {"locale": "de", "tools": {"alpha": override}})
        with pytest.raises(applier.PackError, match="at least 5"):
            applier.load_pack(path)

    def test_rejects_nested_artifact(self, tmp_path):
        override = _tool_override()
        override["faqs"][0]["a"] = "LSI: Kredit, Zins, Tilgung und Laufzeit."
        path = self._write_pack(tmp_path, {"locale": "de", "tools": {"alpha": override}})
        with pytest.raises(applier.PackError, match="lsi_scaffold"):
            applier.load_pack(path)

    def test_rejects_reviewer_without_date(self, tmp_path):
        override = _tool_override(reviewer="Native Reviewer")
        path = self._write_pack(tmp_path, {"locale": "de", "tools": {"alpha": override}})
        with pytest.raises(applier.PackError, match="together"):
            applier.load_pack(path)
