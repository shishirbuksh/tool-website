"""Blog engine integration tests: index, pillar, post, 404s, CSP nonce, no-cache headers."""

import os
import re

import yaml
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, base_url="http://127.0.0.1", client=("127.0.0.1", 80))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _blog_posts():
    with open(os.path.join(BASE_DIR, "data", "blog.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)["posts"]


class TestBlogPages:
    def test_blog_index_200(self):
        resp = client.get("/blog")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_blog_pillar_200(self):
        resp = client.get("/blog/calculators")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_blog_post_200(self):
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        assert "EMI Calculator Online Free" in resp.text

    def test_blog_post_404_unknown_slug(self):
        resp = client.get("/blog/calculators/no-such-post-xyz")
        assert resp.status_code == 404

    def test_blog_pillar_404(self):
        resp = client.get("/blog/no-such-pillar-xyz")
        assert resp.status_code == 404

    def test_blog_post_404_wrong_pillar(self):
        resp = client.get("/blog/developer-tools/emi-calculator-guide")
        assert resp.status_code == 404

    def test_blog_csp_nonce_present(self):
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        assert 'nonce="' in resp.text
        csp = resp.headers.get("content-security-policy", "")
        assert "nonce-" in csp

    def test_blog_no_cache_header(self):
        # Panel verdict (Speaker 3): public short-TTL + ETag for crawl efficiency.
        # Index/pillar -> public max-age=300; post -> public max-age=3600 + ETag.
        for path in ("/blog", "/blog/calculators"):
            resp = client.get(path)
            assert resp.status_code == 200
            cc = resp.headers.get("cache-control", "")
            assert "public" in cc
            assert "max-age=300" in cc
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        cc = resp.headers.get("cache-control", "")
        assert "public" in cc
        assert "max-age=3600" in cc
        assert resp.headers.get("etag"), "post ETag missing"
        # Conditional request -> 304
        etag = resp.headers["etag"]
        resp2 = client.get("/blog/calculators/emi-calculator-guide", headers={"if-none-match": etag})
        assert resp2.status_code == 304


class TestBlogContentGuards:
    def test_blog_keywords_capped_12(self):
        bad = {s: len(v.get("keywords") or []) for s, v in _blog_posts().items() if len(v.get("keywords") or []) > 12}
        assert not bad, f"keyword cap breached: {bad}"

    def test_blog_keywords_no_financial_advice(self):
        bad = [s for s, v in _blog_posts().items() if "is this financial advice" in [str(k).lower() for k in (v.get("keywords") or [])]]
        assert not bad, f"zero-volume KW present: {bad}"

    def test_blog_body_no_dup_chrome(self):
        bad_toc, bad_kt, bad_try, bad_stub, bad_nav = [], [], [], [], []
        bad_take_div, bad_cta, bad_see = [], [], []
        for s, v in _blog_posts().items():
            body = str(v.get("body_html", ""))
            if re.search(r"<h2[^>]*>\s*Table of Contents\s*</h2>", body, re.I):
                bad_toc.append(s)
            if re.search(r"<h2[^>]*>\s*Key Takeaways\s*</h2>", body, re.I):
                bad_kt.append(s)
            if re.search(r"<h2[^>]*>\s*Try the Free[^<]*</h2>", body):
                bad_try.append(s)
            if re.search(r"Short answers.*?#faqs", body):
                bad_stub.append(s)
            if 'aria-label="Table of Contents"' in body:
                bad_nav.append(s)
            if re.search(r"takeaways", body, re.I):
                bad_take_div.append(s)
            if 'class="cta-box"' in body:
                bad_cta.append(s)
            if "See the structured FAQ section" in body:
                bad_see.append(s)
        assert not bad_toc, f"in-body TOC: {bad_toc}"
        assert not bad_kt, f"in-body takeaways H2: {bad_kt}"
        assert not bad_try, f"in-body try-free H2: {bad_try}"
        assert not bad_stub, f"FAQ stubs: {bad_stub}"
        assert not bad_nav, f"in-body TOC nav: {bad_nav}"
        assert not bad_take_div, f"takeaways remnants: {bad_take_div}"
        assert not bad_cta, f"cta-box remnants: {bad_cta}"
        assert not bad_see, f"reworded FAQ stubs: {bad_see}"

    def test_crypto_faqs_exclude_financial_advice(self):
        crypto = [s for s, v in _blog_posts().items() if str(v.get("pillar", "")) == "ai-crypto"]
        assert crypto, "no ai-crypto posts found"
        bad = [s for s in crypto for f in (_blog_posts()[s].get("faqs") or []) if str(f.get("q", "")).lower().strip() == "is this financial advice?"]
        assert not bad, f"disclaimer Q in FAQPage schema: {bad}"

    def test_body_no_duplicate_methodology_faq_ids(self):
        bad_meth = [s for s, v in _blog_posts().items() if 'id="methodology"' in str(v.get("body_html", ""))]
        bad_faq = [s for s, v in _blog_posts().items() if 'id="faq"' in str(v.get("body_html", ""))]
        assert not bad_meth, f"body id=methodology: {bad_meth}"
        assert not bad_faq, f"body id=faq: {bad_faq}"

    def test_body_no_title_dup_h2(self):
        import difflib

        bad = []
        for s, v in _blog_posts().items():
            title = str(v.get("title", "")).lower()
            m = re.search(r"<h2[^>]*>(.*?)</h2>", str(v.get("body_html", "")), re.I | re.S)
            if not m:
                continue
            first = re.sub(r"<[^>]+>", "", m.group(1)).strip().lower()
            if first == title or difflib.SequenceMatcher(None, first, title).ratio() >= 0.85:
                bad.append(s)
        assert not bad, f"title-dup first H2: {bad}"

    def test_schema_single_breadcrumb_absolute_image(self):
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        assert resp.text.count('"BreadcrumbList"') == 1, "duplicate BreadcrumbList"
        assert '"image": "https://' in resp.text, "relative Article.image"
        assert '"position":' not in resp.text.split('"HowTo"')[1].split('"BreadcrumbList"')[0], "HowToStep position"

    def test_links_coverage(self):
        posts = _blog_posts()
        zero_inline = [s for s, v in posts.items() if 'href="/tool/' not in str(v.get("body_html", ""))]
        assert not zero_inline, f"0 inline tool links: {zero_inline}"
        for slug in ["age-calculator", "mortgage-overpayment-calculator", "savings-account-comparison-calculator", "scientific-calculator"]:
            hits = [s for s, v in posts.items() if slug in (v.get("tools") or []) or f"/tool/{slug}" in str(v.get("body_html", ""))]
            assert hits, f"never linked: {slug}"
        adsense_tools = posts["adsense-youtube-earnings-estimator"].get("tools") or []
        assert "instagram-calculator" in adsense_tools, "instagram not promoted"

    def test_em_allowed_parity(self):
        from app.core.sanitize import sanitize_html

        assert "<em>" in str(sanitize_html("<em>x</em>"))

    def test_takeaway_has_no_description_dup(self):
        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        assert "{{ post.description | truncate(160) }}" not in resp.text

    def test_post_og_matches_meta_not_generic(self):
        import re as _re

        resp = client.get("/blog/calculators/emi-calculator-guide")
        assert resp.status_code == 200
        m = _re.search(r'<meta property="og:title" content="([^"]*)"', resp.text)
        assert m, "og:title missing"
        assert "EMI Calculator Online Free 2026" in m.group(1)
        assert "100+ Free Browser Tools" not in m.group(1)

    def test_pillar_faqpage_matches_visible(self):
        import re as _re

        resp = client.get("/blog/calculators")
        assert resp.status_code == 200
        assert resp.text.count('"FAQPage"') == 1
        summaries = _re.findall(r"<summary[^>]*>(.*?)</summary>", resp.text, _re.S)
        assert len(summaries) == 2
        for s in summaries:
            plain = _re.sub(r"<[^>]+>", "", s).strip()
            assert plain in resp.text

    def test_index_faqpage_matches_visible(self):
        resp = client.get("/blog")
        assert resp.status_code == 200
        assert '"FAQPage"' in resp.text

    def test_breadcrumb_no_fragment(self):
        import re as _re

        for path in ["/tool/emi-calculator", "/blog/calculators/emi-calculator-guide"]:
            resp = client.get(path)
            assert resp.status_code == 200
            blocks = _re.findall(r'"@type"\s*:\s*"BreadcrumbList".*?(?=<script|</head>)', resp.text, _re.S)
            assert blocks, f"no BreadcrumbList on {path}"
            for b in blocks:
                assert "/#tools" not in b, f"fragment breadcrumb on {path}"
            assert "/tools" in resp.text

    def test_faqs_capped_10(self):
        bad = {s: len(v.get("faqs") or []) for s, v in _blog_posts().items() if len(v.get("faqs") or []) > 10}
        assert not bad, f"FAQ cap breached: {bad}"

    def test_body_h2_no_chrome_terms(self):
        ban = re.compile(r"^(key takeaways|takeaways|faqs?|frequently asked questions|methodology|table of contents|on this page|related tools|related guides|try(\s|the|free))\b", re.I)
        bad = []
        for s, v in _blog_posts().items():
            for h in re.findall(r"<h2[^>]*>(.*?)</h2>", str(v.get("body_html", "")), re.S):
                if ban.match(re.sub(r"[^a-z0-9]+", " ", re.sub(r"<[^>]+>", "", h).lower()).strip()):
                    bad.append(f"{s}::{h[:60]}")
        assert not bad, f"chrome H2s: {bad[:8]}"

    def test_body_tables_caption_thead(self):
        bad = []
        for s, v in _blog_posts().items():
            for tbl in re.findall(r"<table.*?</table>", str(v.get("body_html", "")), re.S):
                if "<caption>" not in tbl or "<thead>" not in tbl or len(re.findall(r"<th[ >]", tbl)) < 2:
                    bad.append(s)
                    break
        assert not bad, f"tables missing caption/thead/th: {bad}"

    def test_blog_keywords_unique_case_insensitive(self):
        bad = []
        for s, v in _blog_posts().items():
            kws = [str(k).lower() for k in (v.get("keywords") or [])]
            if len(kws) != len(set(kws)):
                bad.append(s)
        assert not bad, f"dupe keywords: {bad}"

    def test_faq_answers_at_most_two_tool_links(self):
        # One link is the norm; comparison answers (e.g. SIP vs FD) may link both tools.
        bad = []
        for s, v in _blog_posts().items():
            for f in (v.get("faqs") or []):
                if len(re.findall(r'href="/tool/', str(f.get("a", "")))) > 2:
                    bad.append(f"{s}::{f.get('q', '')[:50]}")
        assert not bad, f"multi-link answers: {bad[:8]}"
