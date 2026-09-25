"""Tools catalog coverage: every tool has metadata, dates, and a template."""

import os

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH = os.path.join(BASE_DIR, "data", "tools.yaml")
TOOLS_DIR = os.path.join(BASE_DIR, "templates", "tools")

MIN_TOOLS = 100


def _load() -> dict:
    with open(YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["tools"]


class TestToolsYamlCoverage:
    def test_minimum_tool_count(self) -> None:
        assert len(_load()) >= MIN_TOOLS, "tools.yaml must keep full catalog coverage"

    def test_required_fields(self) -> None:
        thin: list[str] = []
        for slug, info in _load().items():
            for field in ("name", "category", "description", "date_modified"):
                if not str(info.get(field, "")).strip():
                    thin.append(f"{slug}: missing {field}")
        assert not thin, f"Tools missing required fields: {thin[:10]}"

    def test_templates_coverage(self) -> None:
        missing: list[str] = []
        for slug in _load():
            fname = slug.replace("-", "_") + ".html"
            if not os.path.exists(os.path.join(TOOLS_DIR, fname)):
                missing.append(f"{slug} -> {fname}")
        assert not missing, f"Tools without templates: {missing[:10]}"
