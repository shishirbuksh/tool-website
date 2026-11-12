"""Regression guards for template HTML/CSS/a11y fixes, meta/schema hygiene, and SEO quality."""

from __future__ import annotations

import glob
import os
import re

import yaml
from fastapi.testclient import TestClient

from app.main import app

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(BASE_DIR, "templates", "tools")
TOOLS_YAML = os.path.join(BASE_DIR, "data", "tools.yaml")
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

client = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 80))


def _load_tools() -> dict:
    with open(TOOLS_YAML, encoding="utf-8") as f:
        return yaml.load(f, Loader=_YAML_LOADER)["tools"]


class TestTemplateHygieneRegressions:
    def test_no_broken_metric_modifier_classes(self) -> None:
        bad = []
        for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*.html"))):
            with open(path, encoding="utf-8") as f:
                s = f.read()
            if re.search(r"text-base-content--(?:sm|md|lg|xl)\b", s):
                bad.append(os.path.basename(path))
        assert not bad, f"Broken metric CSS modifiers found: {bad}"

    def test_no_broken_transition_var(self) -> None:
        bad = []
        for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*.html"))):
            with open(path, encoding="utf-8") as f:
                if "var(--transition-all" in f.read():
                    bad.append(os.path.basename(path))
        assert not bad, f"Broken CSS transition var found: {bad}"

    def test_no_undefined_seo_variable_in_tool_templates(self) -> None:
        bad = []
        for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*.html"))):
            with open(path, encoding="utf-8") as f:
                s = f.read()
            if re.search(r"\{\{[^\n]*\bseo\.(?!data)[a-zA-Z0-9_]+[^\n]*\}\}", s):
                bad.append(os.path.basename(path))
        assert not bad, f"Undefined 'seo.' reference in tool template: {bad}"

    def test_all_tool_imgs_have_width_and_height(self) -> None:
        missing = []
        for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*.html"))):
            with open(path, encoding="utf-8") as f:
                s = f.read()
            for m in re.finditer(r"<img\b[^>]*>", s, re.I | re.S):
                tag = m.group(0)
                if not (re.search(r"\bwidth\s*=", tag, re.I) and re.search(r"\bheight\s*=", tag, re.I)):
                    missing.append(f"{os.path.basename(path)}: {tag[:80]}")
        assert not missing, f"<img> missing explicit width/height: {missing[:10]}"

    def test_all_tool_buttons_have_explicit_type(self) -> None:
        missing = []
        for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*.html"))):
            with open(path, encoding="utf-8") as f:
                s = f.read()
            for _m in re.finditer(r"<button\b(?![^>]*\btype=)[^>]*>", s, re.I):
                missing.append(os.path.basename(path))
                break
        assert not missing, f"<button> missing type= attribute: {missing[:10]}"


class TestMetaSchemaAndRoutingRegressions:
    def test_tool_pages_have_english_schema_and_no_article_dates(self) -> None:
        resp = client.get("/tool/seo-writing-assistant")
        assert resp.status_code == 200
        assert 'property="article:published_time"' not in resp.text
        assert 'property="article:modified_time"' not in resp.text
        assert '"inLanguage":"en"' in resp.text or '"inLanguage": "en"' in resp.text
        assert "/tools?q={search_term_string}" in resp.text
        assert 'name="twitter:image:alt"' in resp.text
        assert "FREE SEO WRITING" in resp.text

    def test_blog_post_keeps_article_dates(self) -> None:
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        assert 'property="article:published_time"' in resp.text
        assert 'property="article:modified_time"' in resp.text

    def test_trailing_slash_returns_301_end_to_end(self) -> None:
        resp = client.get("/tools/?q=crypto", follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] == "/tools?q=crypto"

    def test_tools_directory_has_category_section_and_query_param_js(self) -> None:
        resp = client.get("/tools")
        assert resp.status_code == 200
        assert "category-section" in resp.text
        bundle_path = os.path.join(BASE_DIR, "static", "js", "tools.js")
        with open(bundle_path, encoding="utf-8") as f:
            js = f.read()
        assert "URLSearchParams" in js


class TestContentAndH1Regressions:
    def test_no_synthetic_use_cases_keyword_stuffing(self) -> None:
        hits = []
        for slug, info in _load_tools().items():
            ab = str(info.get("about_body", ""))
            if "Common Use Cases" in ab or "Access a verified" in ab:
                hits.append(slug)
        assert not hits, f"Synthetic keyword-stuffing block still present: {hits[:10]}"

    def test_no_mismatched_prediction_faq_on_calculators(self) -> None:
        hits = []
        for slug, info in _load_tools().items():
            if "prediction" in slug:
                continue
            for faq in info.get("faqs") or []:
                q = str(faq.get("q", faq.get("question", ""))).lower()
                if "prediction" in q:
                    hits.append(slug)
                    break
        assert not hits, f"Off-topic prediction FAQ found: {hits}"

    def test_target_tools_h1_contains_core_topic(self) -> None:
        checks = {
            "/tool/color-palette-extractor": ("COLOR PALETTE", "EXTRACTOR"),
            "/tool/color-palette-generator": ("COLOR PALETTE", "GENERATOR"),
            "/tool/color-contrast-checker": ("COLOR CONTRAST", "CHECKER"),
            "/tool/crypto-fear-greed-index-tracker": ("CRYPTO FEAR &amp; GREED", "INDEX TRACKER"),
            "/tool/mortgage-overpayment-calculator": ("MORTGAGE OVERPAYMENT", "CALCULATOR"),
        }
        for path, (part1, part2) in checks.items():
            resp = client.get(path)
            assert resp.status_code == 200
            m = re.search(r"<h1\b[^>]*>(.*?)</h1>", resp.text, re.S | re.I)
            assert m, f"Missing <h1> on {path}"
            h1 = m.group(1)
            assert part1 in h1 and part2 in h1, f"{path} H1 mismatch: {h1}"
