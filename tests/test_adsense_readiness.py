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


def test_tool_etag_and_304_conditional_caching():
    """Verify tool pages return ETags and respond with 304 Not Modified on If-None-Match & If-Modified-Since."""
    res = client.get("/tool/emi-calculator")
    assert res.status_code == 200
    etag = res.headers.get("etag")
    lm = res.headers.get("last-modified")
    assert etag, "Tool page must return an ETag header"
    assert lm, "Tool page must return a Last-Modified header"
    res304 = client.get("/tool/emi-calculator", headers={"if-none-match": etag})
    assert res304.status_code == 304
    assert res304.headers.get("etag") == etag
    res304_ims = client.get("/tool/emi-calculator", headers={"if-modified-since": lm})
    assert res304_ims.status_code == 304


def test_blog_post_etag_and_304_conditional_caching():
    """Verify blog post pages return ETags and respond with 304 Not Modified on conditional requests."""
    res = client.get("/blog/calculators/emi-calculator-guide")
    assert res.status_code == 200
    etag = res.headers.get("etag")
    lm = res.headers.get("last-modified")
    assert etag, "Blog post must return an ETag header"
    assert lm, "Blog post must return a Last-Modified header"
    res304 = client.get("/blog/calculators/emi-calculator-guide", headers={"if-none-match": etag})
    assert res304.status_code == 304
    assert res304.headers.get("etag") == etag
    res304_ims = client.get("/blog/calculators/emi-calculator-guide", headers={"if-modified-since": lm})
    assert res304_ims.status_code == 304


def test_ads_txt_and_public_static_routes():
    """Verify /ads.txt and all legal static routes serve 200 OK with proper headers."""
    ads_res = client.get("/ads.txt")
    assert ads_res.status_code == 200
    assert "text/plain" in ads_res.headers.get("content-type", "")
    assert "pub-6310719489589992" in ads_res.text
    assert "google.com, pub-6310719489589992, DIRECT, f08c47fec0942fa0" in ads_res.text

    robots_res = client.get("/robots.txt")
    assert robots_res.status_code == 200
    assert "Allow: /ads.txt" in robots_res.text
    assert "Allow: /sitemap.xml" in robots_res.text

    sitemap_res = client.get("/sitemap.xml")
    assert sitemap_res.status_code == 200
    assert "application/xml" in sitemap_res.headers.get("content-type", "")
    assert "/privacy-policy" in sitemap_res.text
    assert "/terms-of-service" in sitemap_res.text
    assert "love-calculator" not in sitemap_res.text
    assert "crypto-price-prediction" not in sitemap_res.text

    # HEAD /ads.txt
    ads_head = client.head("/ads.txt")
    assert ads_head.status_code == 200
    assert "text/plain" in ads_head.headers.get("content-type", "")

    for route in (
        "/privacy-policy",
        "/terms-of-service",
        "/privacy",
        "/terms",
        "/disclaimer",
        "/about",
        "/contact",
        "/student-hub",
    ):
        res = client.get(route)
        assert res.status_code == 200, f"{route} returned {res.status_code}"
        assert "text/html" in res.headers.get("content-type", "")
        assert "Please click here if you are not redirected" not in res.text


def test_calculator_default_states_and_prepayment_math():
    """Verify EMI Calculator and Crypto Predictor render valid initial metrics without stuck/negative states."""
    emi_res = client.get("/tool/emi-calculator")
    assert emi_res.status_code == 200
    assert "$-1,542" not in emi_res.text
    assert "128.2%" not in emi_res.text
    assert "$2,318" in emi_res.text
    assert "$35,415" in emi_res.text
    assert "34 mo" in emi_res.text
    assert "29.0%" in emi_res.text

    crypto_res = client.get("/tool/crypto-price-prediction")
    assert crypto_res.status_code == 200
    assert "Awaiting Data..." not in crypto_res.text
    assert "$96,450.00" in crypto_res.text
    assert "$98,820.00" in crypto_res.text
    assert "Uptrend" in crypto_res.text


def test_quarantined_ymyl_and_novelty_tools_have_noindex():
    """High-risk/speculative tools and guides must carry noindex, follow until AdSense approval."""
    for tool_slug in (
        "love-calculator",
        "crypto-price-prediction",
        "meme-coin-detector",
        "airdrop-finder",
        "crypto-scam-checker",
        "crypto-red-flag-self-assessment-tool",
    ):
        res = client.get(f"/tool/{tool_slug}")
        assert res.status_code == 200
        assert '<meta name="robots" content="noindex, follow">' in res.text

    for blog_path in (
        "/blog/ai-crypto/crypto-price-prediction-how-it-works",
        "/blog/ai-crypto/meme-coin-detector-guide",
        "/blog/productivity-utilities/love-calculator-explained-fun",
    ):
        res = client.get(blog_path)
        assert res.status_code == 200
        assert '<meta name="robots" content="noindex, follow">' in res.text

    normal_tool = client.get("/tool/emi-calculator")
    assert '<meta name="robots" content="index, follow">' in normal_tool.text


def test_copy_free_of_keyword_stuffing_and_desk_attributions():
    """Verify zero synthetic keyword stuffing or fictional desk attributions."""
    with open(ROOT / "data" / "tools.yaml", encoding="utf-8") as f:
        tools_raw = f.read()
    with open(ROOT / "data" / "blog.yaml", encoding="utf-8") as f:
        blog_raw = f.read()

    assert "Research Desk" not in tools_raw
    assert "Research Desk" not in blog_raw
    assert "no signup free" not in tools_raw
    assert "15 vs 20 year emi amount with amortization table" not in tools_raw
    assert "what is safe emi for my salary 2026" not in tools_raw
    assert "operates as an instant" not in tools_raw
