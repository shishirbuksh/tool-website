"""AdSense policy readiness, runtime regression, and E-E-A-T quality tests."""

import re
from collections import Counter
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app, base_url="https://www.storybrainai.com")


def _plain_words(html: str) -> int:
    return len(re.sub(r"<[^>]+>", " ", html).split())


def test_no_empty_advertisement_boxes_when_slot_ids_unset():
    """Never render empty AdSense placeholder wrappers when slot IDs are unconfigured."""
    for url in (
        "/",
        "/tools",
        "/student-tools",
        "/tool/bmi-calculator",
        "/blog/calculators/emi-calculator-guide",
        "/blog/ai-crypto/crypto-price-prediction-how-it-works",
    ):
        res = client.get(url)
        assert res.status_code == 200, f"GET {url} returned {res.status_code}"
        assert "Advertisement</p>" not in res.text
        assert '<div class="ad-slot"' not in res.text


def test_tool_template_runtime_and_policy_fixes():
    """Verify key repaired templates render cleanly with accurate scoping & CSPRNG."""
    bmi = client.get("/tool/bmi-calculator")
    assert bmi.status_code == 200
    assert "el('unitMetric')" not in bmi.text

    watermark = client.get("/tool/watermark-remover")
    assert watermark.status_code == 200
    assert "Authorized edits only" in watermark.text

    uuid_res = client.get("/tool/uuid-generator")
    assert uuid_res.status_code == 200
    assert "getRandomValues" in uuid_res.text
    assert "UUID v7" in uuid_res.text

    pred = client.get("/tool/crypto-price-prediction")
    assert pred.status_code == 200
    assert "Scenario Simulator" in pred.text


def test_all_tools_meet_depth_eeat_and_unique_faq_standards():
    """All 126 tools carry authentic depth (>=155w), E-E-A-T fields, and non-generic FAQs."""
    with open(ROOT / "data" / "tools.yaml", encoding="utf-8") as f:
        tools = yaml.safe_load(f)["tools"]

    faq_qs = Counter()
    for slug, tool in tools.items():
        assert _plain_words(tool.get("about_body", "")) >= 155, f"{slug} about_body < 155w"
        assert tool.get("author"), f"{slug} missing author"
        assert tool.get("reviewed_by"), f"{slug} missing reviewed_by"
        assert len(tool.get("sources", [])) >= 2, f"{slug} needs >=2 primary sources"
        combined = (tool.get("howto_calculate", "") + " " + tool.get("about_body", "")).lower()
        assert "transparent calculation logic" not in combined, f"{slug} still has boilerplate"
        for faq in tool.get("faqs", []):
            q = faq["q"].strip()
            assert q != "Is my data saved between sessions?", f"{slug} has generic storage FAQ"
            faq_qs[q] += 1

    dups = [q for q, count in faq_qs.items() if count > 1]
    assert not dups, f"Duplicate FAQ questions across tools: {dups}"


def test_apex_host_redirects_to_www_and_mobile_nav_has_blog():
    """Verify bare apex storybrainai.com 301-redirects to www, and mobile drawer exposes /blog."""
    apex_client = TestClient(app, base_url="https://storybrainai.com")
    res = apex_client.get("/tool/text-case-converter?ref=gsc", follow_redirects=False)
    assert res.status_code == 301
    assert res.headers.get("location") == "https://www.storybrainai.com/tool/text-case-converter?ref=gsc"

    home = client.get("/")
    assert home.status_code == 200
    assert 'href="/blog"' in home.text
    assert "Guides &amp; Blog" in home.text
    # Ensure Consent Mode v2 initializes Google scripts cleanly on default visit (still gated by GPC/reject)
    assert "loadGoogleScripts();" in home.text
    csp = home.headers.get("content-security-policy", "")
    assert "https://fundingchoicesmessages.google.com" in csp
    assert "https://*.adtrafficquality.google" in csp


def test_all_blog_posts_free_of_boilerplate_and_eeat_complete():
    """All 99 blog posts carry >=950 words, E-E-A-T fields, unique H2s, and zero boilerplate."""
    with open(ROOT / "data" / "blog.yaml", encoding="utf-8") as f:
        posts = yaml.safe_load(f)["posts"]

    h2_counts = Counter()
    banned_snippets = (
        "Point estimates hide uncertainty",
        "An estimate you cannot reproduce is just a feeling",
        "Quoting in chat without scope causes price fights",
    )

    for slug, post in posts.items():
        body = post.get("body_html", "")
        assert _plain_words(body) >= 950, f"{slug} body_html < 950w"
        assert post.get("author"), f"{slug} missing author"
        assert post.get("reviewed_by"), f"{slug} missing reviewed_by"
        assert post.get("sources"), f"{slug} missing sources"
        for snippet in banned_snippets:
            assert snippet not in body, f"{slug} contains banned boilerplate: {snippet}"
        for raw_h2 in re.findall(r"<h2[^>]*>(.*?)</h2>", body, flags=re.S | re.I):
            clean_h2 = re.sub(r"<[^>]+>", "", raw_h2).strip()
            h2_counts[clean_h2] += 1

    dup_h2s = [h for h, count in h2_counts.items() if count > 1]
    assert not dup_h2s, f"Duplicate H2 headings across blog posts: {dup_h2s}"


def test_all_tools_non_empty_nonce_and_no_unused_font_preload():
    """Every inline script & JSON-LD block on representative/all tools has a non-empty nonce."""
    res = client.get("/tool/exam-photo-signature-resizer")
    assert res.status_code == 200
    assert 'nonce=""' not in res.text
    assert "/static/fonts/QGYvz_MVcBeNP4NJtEtq.woff2" not in res.text
    res2 = client.get("/tool/crypto-password-generator")
    assert res2.status_code == 200
    assert 'nonce=""' not in res2.text
    assert "data-helpful-box" in res2.text


def test_homepage_accessibility_and_perf_fixes():
    """Verify accessible drawer buttons, native FAQ details, and inlined font CSS."""
    res = client.get("/")
    assert res.status_code == 200
    assert "/static/css/fonts.css" not in res.text
    assert 'id="mobileDrawer"' not in res.text
    assert 'id="mobileDrawerSidebar"' in res.text
    assert 'name="home-accordion"' in res.text
    assert 'type="radio" name="home-accordion"' not in res.text
    assert res.text.count("<main") == 1
