"""Schema validation for data/tools.yaml: slugs<->templates, related slugs, dates, escapes."""

import os
import re

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH = os.path.join(BASE_DIR, "data", "tools.yaml")
TOOLS_DIR = os.path.join(BASE_DIR, "templates", "tools")

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_raw_and_data():
    with open(YAML_PATH, encoding="utf-8") as f:
        raw = f.read()
    with open(YAML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)["tools"]
    return raw, data


class TestToolsYamlSchema:
    def test_slugs_have_templates(self):
        _, data = _load_raw_and_data()
        missing = []
        for slug in data:
            fname = slug.replace("-", "_") + ".html"
            if not os.path.exists(os.path.join(TOOLS_DIR, fname)):
                missing.append(f"{slug} -> {fname}")
        assert not missing, f"Slugs without templates: {missing[:10]}"

    def test_related_slugs_exist(self):
        _, data = _load_raw_and_data()
        slugs = set(data)
        bad = []
        for slug, info in data.items():
            for rel in info.get("related_slugs") or []:
                if rel not in slugs:
                    bad.append(f"{slug} -> {rel}")
        assert not bad, f"related_slugs pointing at unknown slugs: {bad[:10]}"

    def test_date_format(self):
        _, data = _load_raw_and_data()
        bad = [s for s, info in data.items() if not DATE_RE.match(str(info.get("date_modified", "")))]
        assert not bad, f"Bad date_modified format: {bad[:10]}"

    def test_no_literal_backslash_xE2(self):
        raw, _ = _load_raw_and_data()
        # The catalog must contain real UTF-8 (e.g. em dash) — not literal
        # backslash escapes like \xE2 / \xC3 left over from mojibake.
        assert "\\xE2" not in raw, "data/tools.yaml contains literal \\xE2 escapes (use real — instead)"
        assert "\\xC3" not in raw, "data/tools.yaml contains literal \\xC3 escapes (use real × instead)"
