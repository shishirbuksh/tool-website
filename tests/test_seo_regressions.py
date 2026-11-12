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


class TestSeoAuditRevisions2026:
    def test_pillar_page_has_breadcrumb_and_twitter_alt(self) -> None:
        import json as _json

        resp = client.get("/blog/calculators")
        assert resp.status_code == 200
        assert 'name="twitter:image"' in resp.text
        assert 'name="twitter:image:alt"' in resp.text
        ld_matches = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            resp.text,
            re.S | re.I,
        )
        assert ld_matches, "Missing JSON-LD on /blog/calculators"
        types: list[str] = []
        bc_items: list[dict] = []
        for raw_json in ld_matches:
            doc = _json.loads(raw_json)
            nodes = doc.get("@graph", [doc]) if isinstance(doc, dict) else doc
            for node in nodes:
                if isinstance(node, dict):
                    t = node.get("@type")
                    if t:
                        types.append(str(t))
                    if t == "BreadcrumbList":
                        bc_items = node.get("itemListElement", [])
        assert "BreadcrumbList" in types
        assert len(bc_items) == 3

    def test_llms_txt_includes_student_tools(self) -> None:
        resp = client.get("/llms.txt")
        assert resp.status_code == 200
        assert "/student-tools" in resp.text

    def test_sitemap_page_decannibalized_from_generator(self) -> None:
        resp = client.get("/sitemap")
        assert resp.status_code == 200
        assert "HTML Sitemap" in resp.text
        assert "XML Sitemap Generator" not in resp.text.split("</title>")[0]
        tools = _load_tools()
        assert "sitemap generator" not in tools["sitemap-generator"]["meta_title"].lower() or (
            "html sitemap" not in tools["sitemap-generator"]["meta_title"].lower()
        )

    def test_sw_js_precaches_existing_hashed_css(self) -> None:
        sw_path = os.path.join(BASE_DIR, "static", "sw.js")
        with open(sw_path, encoding="utf-8") as f:
            sw_text = f.read()
        m = re.search(r"/static/css/(app\.[0-9a-f]+\.css)", sw_text)
        assert m, "static/sw.js must precache hashed app.<hash>.css"
        css_file = os.path.join(BASE_DIR, "static", "css", m.group(1))
        assert os.path.exists(css_file), f"SW precached CSS missing on disk: {css_file}"

    def test_no_mismatched_heading_closing_tags_in_tool_templates(self) -> None:
        mismatched = []
        heading_pair_re = re.compile(r"<h([1-6])\b[^>]*>(?:(?!</?h[1-6]\b).)*?</h([1-6])>", re.S | re.I)
        for path in sorted(glob.glob(os.path.join(TOOLS_DIR, "*.html"))):
            with open(path, encoding="utf-8") as f:
                s = f.read()
            for m in heading_pair_re.finditer(s):
                if m.group(1) != m.group(2):
                    mismatched.append(f"{os.path.basename(path)}: <h{m.group(1)}>...</h{m.group(2)}>")
        assert not mismatched, f"Mismatched heading tags found: {mismatched}"

    def test_tool_templates_hero_badges_and_subtitle_binding(self) -> None:
        banned_label_re = re.compile(
            r"^(?:Free Tool|Developer Tool|SEO Tool|Business Tool|Business|Productivity Tool|AI &amp; Text|AI & Text|.*\bEngine)$"
        )
        inline_badge_re = re.compile(r">(Free Tool|Developer Tool|SEO Tool|Business Tool|Business|Productivity Tool|AI &amp; Text|AI & Text|[^<]{1,40}\bEngine)<")
        hero_macro_re = re.compile(r'tool_hero_section\(\s*["\'][^"\']+["\']\s*,\s*["\']([^"\']+)["\']')
        missing_binding = []
        generic_badges = []
        paths = sorted(glob.glob(os.path.join(TOOLS_DIR, "*.html")))
        assert len(paths) == 126
        for path in paths:
            with open(path, encoding="utf-8") as f:
                s = f.read()
            if "seo_data.description" not in s:
                missing_binding.append(os.path.basename(path))
            macro_m = hero_macro_re.search(s[:1500])
            if macro_m:
                if banned_label_re.match(macro_m.group(1).strip()):
                    generic_badges.append(os.path.basename(path))
            else:
                hero_clean = re.sub(r"<option\b[^>]*>.*?</option>", "", s[:2500], flags=re.S | re.I)
                if inline_badge_re.search(hero_clean):
                    generic_badges.append(os.path.basename(path))
        assert not missing_binding, f"Tool templates missing seo_data.description binding: {missing_binding}"
        assert not generic_badges, f"Generic or Engine hero badges remain: {generic_badges}"

    def test_pdf_converter_and_airdrop_finder_truthfulness(self) -> None:
        tools = _load_tools()
        pdf_meta = tools["pdf-converter"]
        pdf_meta_blob = " ".join(
            [pdf_meta.get("meta_title", ""), pdf_meta.get("description", ""), *(pdf_meta.get("keywords") or [])]
        ).lower()
        assert "word to pdf" not in pdf_meta_blob
        assert "pdf to word" not in pdf_meta_blob
        assert "split" not in pdf_meta_blob

        resp_pdf = client.get("/tool/pdf-converter")
        assert resp_pdf.status_code == 200
        assert "Images &amp; Text to PDF Converter" in resp_pdf.text or "Images & Text to PDF Converter" in resp_pdf.text

        ad_meta = tools["airdrop-finder"]
        assert "upcoming crypto airdrops list 2026" not in [k.lower() for k in (ad_meta.get("keywords") or [])]
        resp_ad = client.get("/tool/airdrop-finder")
        assert resp_ad.status_code == 200
        assert "Sybil Hygiene Checklist" in resp_ad.text
        assert "Historical TGE Benchmarks" in resp_ad.text
        assert ">LIVE<" not in resp_ad.text

    def test_blog_cleanliness_and_eeat_rendering(self) -> None:
        blog_path = os.path.join(BASE_DIR, "data", "blog.yaml")
        with open(blog_path, encoding="utf-8") as f:
            posts = yaml.load(f, Loader=_YAML_LOADER)["posts"]
        assert len(posts) == 99
        stuffed = [s for s, p in posts.items() if "Frequently Explored Topics" in p.get("body_html", "")]
        bracketed = [
            s
            for s, p in posts.items()
            if "[" in p.get("description", "") or "]" in p.get("description", "") or "[" in p.get("meta_title", "")
        ]
        assert not stuffed, f"Synthetic stuffing remains in blog posts: {stuffed}"
        assert not bracketed, f"Bracket clickbait remains in blog metadata: {bracketed}"

        resp_q = client.get("/blog/business-operations/quotation-vs-proforma-invoice-guide")
        assert resp_q.status_code == 200
        assert "(L1)" not in resp_q.text
        assert "My L1 rule" not in resp_q.text
        assert "Primary Sources" in resp_q.text
        assert "cbic-gst.gov.in" in resp_q.text

    def test_eeat_sources_render_on_priority_ymyl_tools(self) -> None:
        for slug in ("crypto-tax-calculator", "salary-calculator", "mortgage-overpayment-calculator"):
            resp = client.get(f"/tool/{slug}")
            assert resp.status_code == 200
            assert "Primary Sources" in resp.text
            assert '"citation"' in resp.text
