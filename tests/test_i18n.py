"""i18n tests: locale routing, hreflang, per-locale SEO, sitemap index, keyword guards."""

from fastapi.testclient import TestClient


class TestI18nCore:
    def test_supported_locales(self):
        from app.core.i18n import SUPPORTED_LOCALES, hreflang_links, localize_path, normalize_locale

        assert set(SUPPORTED_LOCALES) == {"en", "hi", "es", "fr"}
        assert normalize_locale("HI") == "hi"
        assert normalize_locale("xx") == "en"
        assert localize_path("/tool/emi-calculator", "hi") == "/hi/tool/emi-calculator"
        assert localize_path("/tool/emi-calculator", "en") == "/tool/emi-calculator"
        assert localize_path("/hi/tool/x", "es") == "/es/tool/x"
        links = hreflang_links("https://www.storybrainai.com", "/tool/emi-calculator")
        codes = {link["hreflang"] for link in links}
        assert {"en", "hi", "es", "fr", "x-default"} <= codes

    def test_ui_strings_complete(self):
        from app.core.i18n import UI_STRINGS, t

        keys = set(UI_STRINGS["en"].keys())
        assert len(keys) >= 10
        for loc in ("hi", "es", "fr"):
            missing = keys - set(UI_STRINGS[loc].keys())
            assert not missing, f"{loc} missing {missing}"
        assert t("nav.home", "hi") != t("nav.home", "en")


class TestI18nSeo:
    def test_tool_hi_override(self, settings):
        from app.services.seo_service import SeoService

        svc = SeoService(settings)
        en = svc.get_seo("emi-calculator", locale="en")
        hi = svc.get_seo("emi-calculator", locale="hi")
        assert en.locale == "en" and hi.locale == "hi"
        assert hi.name != en.name
        assert hi.url.endswith("/hi/tool/emi-calculator")
        assert en.url.endswith("/tool/emi-calculator")
        assert len(hi.keywords) <= 8
        assert 120 <= len(hi.description) <= 200

    def test_tool_es_fr_override(self, settings):
        from app.services.seo_service import SeoService

        svc = SeoService(settings)
        en = svc.get_seo("emi-calculator", locale="en")
        for loc, tail in (("es", "/es/tool/emi-calculator"), ("fr", "/fr/tool/emi-calculator")):
            over = svc.get_seo("emi-calculator", locale=loc)
            assert over.locale == loc
            assert over.name != en.name
            assert over.url.endswith(tail)
            assert len(over.keywords) <= 8
            assert 120 <= len(over.description) <= 200

    def test_all_pilots_have_es_fr(self, settings):
        from app.core.tool_data import ToolDataLoader

        pilots = [
            "emi-calculator", "eway-bill-calculator", "crypto-tax-calculator", "age-calculator",
            "bmi-calculator", "fuel-cost-calculator", "salary-calculator", "gst-calculator",
            "invoice-generator", "word-counter",
            # Batch 2 (2026-10-10): high-traffic tools
            "qr-generator", "sip-calculator", "password-generator", "seo-writing-assistant",
            "meme-generator", "quotation-generator", "percentage-calculator", "uuid-generator",
            "json-formatter-validator", "image-compressor", "calculator", "mrr-calculator",
            # Batch 3: finance winners + viral + flagship tools
            "mortgage-overpayment-calculator", "adsense-calculator", "fd-calculator", "love-calculator",
            "image-background-remover", "crypto-price-prediction", "paraphrasing-tool", "resume-generator",
            "pdf-merger", "expense-tracker", "compound-calculator", "freelance-rate-calculator",
            # Batch 4: retirement/creator/image/dev/utility
            "retirement-planning-calculator", "youtube-calculator", "instagram-calculator", "image-converter",
            "image-resizer-cropper", "image-exif-remover", "base64-tool", "regex-tester",
            "meta-tag-generator", "unit-converter", "date-calculator", "text-case-converter",
            # Batch 5: crypto + CSS + doc generators
            "crypto-dca-calculator", "crypto-mining-calculator", "crypto-profit-calculator", "crypto-portfolio-analyzer",
            "crypto-fear-greed-index-tracker", "css-gradient-generator", "css-box-shadow-generator", "css-animation-generator",
            "purchase-order-generator", "sales-order-generator", "service-order-generator", "work-order-generator",
        ]
        all_tools = ToolDataLoader.get_all()
        for slug in pilots:
            i18n = (all_tools[slug].get("i18n") or {})
            for loc in ("hi", "es", "fr"):
                assert loc in i18n, f"{slug} missing {loc}"
                assert len(i18n[loc].get("keywords", [])) <= 8

    def test_all_i18n_overrides_meet_length_guards(self, settings):
        """Lock SEO length/cap rules for every locale override (present + future batches)."""
        from app.core.tool_data import ToolDataLoader

        all_tools = ToolDataLoader.get_all()
        checked = 0
        for slug, info in all_tools.items():
            for loc in ("hi", "es", "fr"):
                over = (info.get("i18n") or {}).get(loc) or {}
                if not over:
                    continue
                checked += 1
                assert over.get("meta_title") and len(over["meta_title"]) <= 70, f"{slug}/{loc} title"
                assert over.get("description") and 120 <= len(over["description"]) <= 200, f"{slug}/{loc} desc"
                assert len(over.get("keywords", [])) <= 8, f"{slug}/{loc} kws"
                assert len(over.get("faqs", [])) >= 3, f"{slug}/{loc} faqs"
        assert checked >= 58 * 3, f"expected 58 tools x 3 locales, got {checked}"

    def test_tool_fallback_en(self, settings):
        from app.services.seo_service import SeoService

        # pick a non-pilot for fallback
        svc2 = SeoService(settings)
        hi = svc2.get_seo("calculator", locale="hi")
        # non-pilot falls back to EN content but keeps locale + localized URL
        assert hi.locale == "hi"
        assert hi.url.endswith("/hi/tool/calculator")

    def test_blog_hi_override(self, settings):
        from app.services.blog_service import BlogService

        svc = BlogService(settings)
        en = svc.get("emi-calculator-guide", locale="en")
        hi = svc.get("emi-calculator-guide", locale="hi")
        assert en is not None and hi is not None
        assert hi.locale == "hi"
        assert hi.title != en.title
        assert hi.url.endswith("/hi/blog/calculators/emi-calculator-guide")

    def test_blog_es_fr_override(self, settings):
        from app.services.blog_service import BlogService

        svc = BlogService(settings)
        en = svc.get("emi-calculator-guide", locale="en")
        assert en is not None
        for loc in ("es", "fr"):
            over = svc.get("emi-calculator-guide", locale=loc)
            assert over is not None
            assert over.locale == loc
            assert over.title != en.title
            assert over.url.endswith(f"/{loc}/blog/calculators/emi-calculator-guide")

    def test_locale_keywords_no_exact_en_collision(self, settings):
        """HI/ES/FR pilot keywords must not exactly duplicate EN primaries (normalized)."""
        import re

        from app.core.tool_data import ToolDataLoader

        def norm(s: str) -> str:
            return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()

        all_tools = ToolDataLoader.get_all()
        en_norms: set[str] = set()
        for _slug, info in all_tools.items():
            for k in info.get("keywords", []) or []:
                en_norms.add(norm(str(k)))
        for slug, info in all_tools.items():
            for loc in ("hi", "es", "fr"):
                over = (info.get("i18n") or {}).get(loc) or {}
                for k in over.get("keywords", []) or []:
                    n = norm(str(k))
                    # Devanagari keywords normalize to "" — only check latin ones
                    if n:
                        assert n not in en_norms, f"{loc.upper()} collision: {slug}:{k}"


class TestI18nRoutes:
    def test_tool_hi_renders(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/hi/tool/emi-calculator")
        assert r.status_code == 200, r.status_code
        assert "text/html" in r.headers.get("content-type", "")
        assert r.headers.get("Content-Language") == "hi"
        assert 'hreflang="hi"' in r.text
        assert 'hreflang="x-default"' in r.text
        assert 'og:locale' in r.text and "hi_IN" in r.text
        assert "/hi/tool/emi-calculator" in r.text  # canonical self

    def test_tool_en_still_ok(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/tool/emi-calculator")
        assert r.status_code == 200
        assert 'hreflang="hi"' in r.text  # EN carries full cluster too

    def test_tool_unknown_locale_404(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        assert c.get("/xx/tool/emi-calculator").status_code == 404
        assert c.get("/en/tool/emi-calculator").status_code == 404

    def test_blog_hi_renders(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/hi/blog/calculators/emi-calculator-guide")
        assert r.status_code == 200, r.status_code
        assert r.headers.get("Content-Language") == "hi"

    def test_tool_es_fr_renders(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        for loc, og in (("es", "es_ES"), ("fr", "fr_FR")):
            r = c.get(f"/{loc}/tool/emi-calculator")
            assert r.status_code == 200, (loc, r.status_code)
            assert r.headers.get("Content-Language") == loc
            assert og in r.text
            assert f"/{loc}/tool/emi-calculator" in r.text
            rb = c.get(f"/{loc}/blog/calculators/emi-calculator-guide")
            assert rb.status_code == 200, (loc, rb.status_code)
            assert rb.headers.get("Content-Language") == loc
            rh = c.get(f"/{loc}/")
            assert rh.status_code == 200, (loc, rh.status_code)
            assert rh.headers.get("Content-Language") == loc

    def test_home_hi_renders(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/hi/")
        assert r.status_code == 200
        assert r.headers.get("Content-Language") == "hi"

    def test_sitemap_locale(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/sitemap-hi.xml")
        assert r.status_code == 200
        assert "/hi/tool/" in r.text
        assert "xhtml:link" in r.text
        for loc in ("es", "fr"):
            rl = c.get(f"/sitemap-{loc}.xml")
            assert rl.status_code == 200, loc
            assert f"/{loc}/tool/" in rl.text
            assert "xhtml:link" in rl.text
        r2 = c.get("/sitemap-index.xml")
        assert r2.status_code == 200
        assert "sitemap-hi.xml" in r2.text
        assert "sitemap-es.xml" in r2.text
        assert "sitemap-fr.xml" in r2.text
        r3 = c.get("/sitemap.xml")
        assert r3.status_code == 200
        assert "xhtml:link" in r3.text  # EN now carries hreflang too
        r4 = c.get("/robots.txt")
        assert "sitemap-hi.xml" in r4.text
        assert "sitemap-es.xml" in r4.text
        assert "sitemap-fr.xml" in r4.text

    def test_language_switcher_present(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        for path in ("/tool/emi-calculator", "/hi/tool/emi-calculator"):
            r = c.get(path)
            assert r.status_code == 200, path
            # Desktop globe switcher + mobile drawer links cover all locales
            for code in ("hi", "es", "fr"):
                assert f"/{code}/tool/emi-calculator" in r.text, (path, code)
            assert 'aria-current="true"' in r.text

    def test_catalog_locale(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        en = c.get("/api/tools/catalog")
        assert en.status_code == 200
        hi = c.get("/api/tools/catalog?lang=hi")
        assert hi.status_code == 200
        assert hi.headers.get("Content-Language") == "hi"
        en_items = {t["url"]: t for t in en.json()}
        hi_items = {t["url"]: t for t in hi.json()}
        assert "/tool/emi-calculator" in en_items
        assert "/hi/tool/emi-calculator" in hi_items
        # Pilot tool translated; non-pilot falls back to EN name with localized URL
        assert hi_items["/hi/tool/emi-calculator"]["name"] != en_items["/tool/emi-calculator"]["name"]
        assert hi_items["/hi/tool/task-manager"]["name"] == en_items["/tool/task-manager"]["name"]
        es = c.get("/api/tools/catalog?lang=es")
        assert any(t["url"].startswith("/es/tool/") for t in es.json())
        # Unknown lang falls back to EN without crashing
        xx = c.get("/api/tools/catalog?lang=xx")
        assert xx.status_code == 200
        assert any(t["url"] == "/tool/emi-calculator" for t in xx.json())

    def test_offline_and_html_sitemap_i18n(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/offline")
        assert r.status_code == 200
        assert 'hreflang="hi"' in r.text
        r2 = c.get("/sitemap")
        assert r2.status_code == 200
        assert 'hreflang="es"' in r2.text

    def test_blog_index_localized(self):
        """Regression: /hi|es|fr/blog must render (prod 404 report, 2026-10-10)."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        for loc in ("hi", "es", "fr"):
            r = c.get(f"/{loc}/blog")
            assert r.status_code == 200, loc
            assert "text/html" in r.headers.get("content-type", "")
            assert r.headers.get("Content-Language") == loc
            assert f'/{loc}/blog/' in r.text or f"/{loc}/blog" in r.text

    def test_blog_pillar_localized(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        for loc in ("hi", "es", "fr"):
            r = c.get(f"/{loc}/blog/calculators")
            assert r.status_code == 200, loc
            assert r.headers.get("Content-Language") == loc


class TestIndexNowLocales:
    def test_sitemap_urls_for(self):
        from scripts.submit_indexnow import sitemap_urls_for

        assert sitemap_urls_for("www.storybrainai.com", include_all=True, locales=[]) == [
            "https://www.storybrainai.com/sitemap.xml"
        ]
        assert sitemap_urls_for("www.storybrainai.com", include_all=True, locales=["hi", "es"]) == [
            "https://www.storybrainai.com/sitemap.xml",
            "https://www.storybrainai.com/sitemap-hi.xml",
            "https://www.storybrainai.com/sitemap-es.xml",
        ]
        # Unknown locales ignored
        assert sitemap_urls_for("www.storybrainai.com", include_all=False, locales=["xx"]) == []
