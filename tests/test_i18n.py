"""i18n tests: English-only routing, SEO metadata, redirects for legacy locale paths,
sitemaps, and removal of language toggles.
"""

from __future__ import annotations

import re
from fastapi.testclient import TestClient


class TestI18nCore:
    def test_supported_locales(self):
        from app.core.i18n import SUPPORTED_LOCALES, hreflang_links, localize_path, normalize_locale

        assert set(SUPPORTED_LOCALES) == {"en"}
        assert normalize_locale("HI") == "en"
        assert normalize_locale("xx") == "en"
        assert localize_path("/tool/emi-calculator", "hi") == "/tool/emi-calculator"
        assert localize_path("/tool/emi-calculator", "en") == "/tool/emi-calculator"
        assert localize_path("/hi/tool/x", "es") == "/tool/x"
        links = hreflang_links("https://www.storybrainai.com", "/tool/emi-calculator")
        codes = {link["hreflang"] for link in links}
        assert {"en", "x-default"} <= codes
        for loc in ("hi", "es", "fr", "de"):
            assert loc not in codes

    def test_ui_strings_complete(self):
        from app.core.i18n import UI_STRINGS, t

        assert "en" in UI_STRINGS
        keys = set(UI_STRINGS["en"].keys())
        assert len(keys) >= 50
        assert t("nav.home", "en") == "Home"
        for k in ("blog.title", "nav.about", "nav.contact", "nav.search", "nav.theme", "nav.menu"):
            assert k in UI_STRINGS["en"], k

    def test_i18n_helpers_edge(self):
        from app.core.i18n import (
            html_lang_for,
            is_supported_locale,
            localize_path,
            localize_url,
            normalize_locale,
            og_locale_for,
            split_locale_path,
            t,
        )

        assert split_locale_path("/HI/tool/x") == ("hi", "/tool/x")
        assert split_locale_path("/hi") == ("hi", "/")
        assert split_locale_path("/") == ("en", "/")
        assert is_supported_locale(None) is False
        assert is_supported_locale(" EN ") is True
        assert is_supported_locale("hi") is False
        assert is_supported_locale("es") is False
        assert normalize_locale("xx") == "en"
        assert og_locale_for("xx") == "en_US"
        assert og_locale_for("en") == "en_US"
        assert html_lang_for("") == "en"
        assert html_lang_for("en") == "en"
        assert t("no.such.key", "en") == "no.such.key"
        assert localize_url("https://www.storybrainai.com/", "/tool/x", "en").endswith("/tool/x")
        assert localize_path("/hi/tool/x", "en") == "/tool/x"


class TestI18nSeo:
    def test_tool_en_seo(self, settings):
        from app.services.seo_service import SeoService

        svc = SeoService(settings)
        en = svc.get_seo("emi-calculator", locale="en")
        assert en.locale == "en"
        assert en.url.endswith("/tool/emi-calculator")
        assert len(en.keywords) <= 8
        assert 100 <= len(en.description) <= 200

    def test_seo_spot_check_tools(self, settings):
        from app.services.seo_service import SeoService

        svc = SeoService(settings)
        for slug in ("gst-calculator", "sip-calculator", "paraphrasing-tool", "emi-calculator"):
            en = svc.get_seo(slug, locale="en")
            assert en.locale == "en", slug
            assert en.url.endswith(f"/tool/{slug}"), slug
            assert en.meta_title and len(en.meta_title) <= 70, slug
            assert 100 <= len(en.description) <= 200, slug
            assert len(en.keywords) <= 8, slug
            assert len(en.faqs) >= 3, slug

    def test_blog_en_seo(self, settings):
        from app.services.blog_service import BlogService

        svc = BlogService(settings)
        en = svc.get("emi-calculator-guide", locale="en")
        assert en is not None
        assert en.locale == "en"
        assert en.url.endswith("/blog/calculators/emi-calculator-guide")


class TestLocaleContentQuality:
    BANNED = [
        "standard mathematical formulas",
        "click calculate",
        "completely free to use",
    ]

    def test_no_banned_boilerplate_english(self):
        from app.core.tool_data import ToolDataLoader

        all_tools = ToolDataLoader.get_all()
        hits = []
        for slug, info in all_tools.items():
            blob = " ".join(
                [
                    str(info.get("description", "")),
                    str(info.get("howto_calculate", "")),
                    " ".join(str(f.get("a", f.get("answer", ""))) for f in (info.get("faqs") or [])),
                ]
            ).lower()
            for phrase in self.BANNED:
                if phrase in blob:
                    hits.append(f"{slug}: {phrase}")
        assert not hits, f"Boilerplate banned phrases: {hits[:15]}"


class TestI18nRoutes:
    def test_tool_en_renders(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/tool/emi-calculator")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert 'lang="en"' in r.text
        assert "og:locale" in r.text and "en_US" in r.text
        assert 'href="https://www.storybrainai.com/tool/emi-calculator"' in r.text
        assert 'hreflang="en"' in r.text
        assert 'hreflang="x-default"' in r.text
        for loc in ("hi", "es", "fr", "de"):
            assert f'hreflang="{loc}"' not in r.text

    def test_legacy_locale_routes_redirect_301(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        cases = [
            ("/hi", "/"),
            ("/hi/", "/"),
            ("/es", "/"),
            ("/de", "/"),
            ("/fr", "/"),
            ("/hi/tools", "/tools"),
            ("/es/tools", "/tools"),
            ("/de/blog", "/blog"),
            ("/fr/blog/calculators/emi-calculator-guide", "/blog/calculators/emi-calculator-guide"),
            ("/hi/tool/emi-calculator", "/tool/emi-calculator"),
            ("/es/tool/emi-calculator", "/tool/emi-calculator"),
            ("/de/tool/emi-calculator", "/tool/emi-calculator"),
            ("/fr/tool/emi-calculator", "/tool/emi-calculator"),
            ("/hi/offline", "/offline"),
            ("/es/sitemap", "/sitemap"),
            ("/de/contact", "/contact"),
        ]
        for path, expected_dest in cases:
            r = c.get(path, follow_redirects=False)
            assert r.status_code == 301, f"{path} returned {r.status_code}"
            assert r.headers["location"] == expected_dest, f"{path} redirected to {r.headers.get('location')}"

    def test_tool_unknown_locale_404(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        assert c.get("/xx/tool/emi-calculator").status_code == 404
        assert c.get("/en/tool/emi-calculator").status_code == 404
        assert c.get("/xx/").status_code == 404
        assert c.get("/xx/blog").status_code == 404
        assert c.get("/xx/blog/calculators").status_code == 404

    def test_no_language_switcher_in_html(self):
        """User requirement: remove multiple language and toggle, only English active."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        for path in ("/", "/tools", "/tool/emi-calculator", "/blog"):
            r = c.get(path)
            assert r.status_code == 200, path
            html = r.text
            # No desktop language dropdown
            assert "dropdown-hover dropdown-end" not in html
            assert "aria-label=\"Language\"" not in html
            # No mobile language drawer block
            assert "id=\"mobile-lang-drawer\"" not in html
            assert "Language selection" not in html
            # No foreign language links in navigation
            assert 'href="/hi/' not in html
            assert 'href="/es/' not in html
            assert 'href="/fr/' not in html
            assert 'href="/de/' not in html

    def test_sitemap_locale(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        # Quarantined / unsupported locale sitemaps return 404
        for loc in ("hi", "es", "fr", "de"):
            rl = c.get(f"/sitemap-{loc}.xml")
            assert rl.status_code == 404, loc
        r2 = c.get("/sitemap-index.xml")
        assert r2.status_code == 200
        for loc in ("hi", "es", "fr", "de"):
            assert f"sitemap-{loc}.xml" not in r2.text, loc
        r3 = c.get("/sitemap.xml")
        assert r3.status_code == 200
        assert "xhtml:link" in r3.text
        assert 'hreflang="hi"' not in r3.text
        assert 'hreflang="de"' not in r3.text
        assert 'hreflang="es"' not in r3.text
        assert 'hreflang="fr"' not in r3.text

        r4 = c.get("/robots.txt")
        for loc in ("hi", "es", "fr", "de"):
            assert f"sitemap-{loc}.xml" not in r4.text, loc

        # EN sitemap alias redirects; unknown locale 404s
        re_ = c.get("/sitemap-en.xml", follow_redirects=False)
        assert re_.status_code == 301, re_.status_code
        assert re_.headers["location"] == "/sitemap.xml"
        assert c.get("/sitemap-xx.xml").status_code == 404

    def test_catalog_english_only(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        en = c.get("/api/tools/catalog")
        assert en.status_code == 200
        items = en.json()
        assert len(items) >= 10
        assert all(t["url"].startswith("/tool/") for t in items)
        # Querying with ?lang=hi falls back to English catalog
        hi = c.get("/api/tools/catalog?lang=hi")
        assert hi.status_code == 200
        assert all(t["url"].startswith("/tool/") for t in hi.json())


class TestIndexNowLocales:
    def test_sitemap_urls_for(self):
        from scripts.submit_indexnow import sitemap_urls_for

        assert sitemap_urls_for("www.storybrainai.com", include_all=True, locales=[]) == [
            "https://www.storybrainai.com/sitemap.xml"
        ]

    def test_contact_form(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        page = c.get("/contact")
        assert page.status_code == 200
        assert page.headers.get("X-Robots-Tag") is None or "noindex" not in page.headers.get("X-Robots-Tag", "")
        r = c.post(
            "/api/contact",
            json={"name": "Alex", "email": "alex@example.com", "message": "Hello from English page"},
            headers={"Origin": "http://127.0.0.1", "Referer": "http://127.0.0.1/contact"},
        )
        assert r.status_code == 200, r.text


class TestMultilingualArchitectureEnhancements:
    def test_schema_and_headings_english(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/tool/emi-calculator")
        assert r.status_code == 200
        assert '"inLanguage": "en"' in r.text
        assert "Frequently Asked Questions" in r.text
        assert "How to Calculate" in r.text
        assert '"priceCurrency": "USD"' in r.text
        assert 'window.sbr.currency = "USD"' in r.text

    def test_hub_page_english(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/calculators")
        assert r.status_code == 200
        assert 'lang="en"' in r.text
        assert "Calculators" in r.text
