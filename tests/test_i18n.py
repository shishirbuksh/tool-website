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
            for k in keys:
                assert str(UI_STRINGS[loc][k]).strip(), f"{loc}.{k} empty"
        assert t("nav.home", "hi") != t("nav.home", "en")
        # New chrome keys present everywhere (blog.title is "Blog" in es/fr by design)
        for k in ("blog.title", "nav.about", "nav.contact", "nav.search", "nav.theme", "nav.menu", "nav.language"):
            assert all(k in UI_STRINGS[loc] for loc in ("en", "hi", "es", "fr")), k

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
        assert is_supported_locale(" EN ") is True  # lenient: strips + lowercases
        assert normalize_locale("xx") == "en"
        assert og_locale_for("xx") == "en_US"
        assert html_lang_for("") == "en"
        assert t("no.such.key", "hi") == "no.such.key"
        assert localize_url("https://www.storybrainai.com/", "/tool/x", "hi").endswith("/hi/tool/x")
        assert localize_path("/hi/tool/x", "es") == "/es/tool/x"


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

    def test_seo_override_spot_check_all_locales(self, settings):
        """Sample pilots beyond emi-calculator across hi/es/fr."""
        from app.services.seo_service import SeoService

        svc = SeoService(settings)
        for slug in ("gst-calculator", "sip-calculator", "paraphrasing-tool"):
            en = svc.get_seo(slug, locale="en")
            for loc in ("hi", "es", "fr"):
                over = svc.get_seo(slug, locale=loc)
                assert over.locale == loc, (slug, loc)
                assert over.name != en.name, (slug, loc)
                assert over.url.endswith(f"/{loc}/tool/{slug}"), (slug, loc)
                assert over.meta_title and len(over.meta_title) <= 70, (slug, loc)
                assert 120 <= len(over.description) <= 200, (slug, loc)
                assert len(over.keywords) <= 8, (slug, loc)
                assert len(over.faqs) >= 3, (slug, loc)
                assert over.howto_calculate or over.howto_steps, (slug, loc)

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
            "emi-calculator",
            "eway-bill-calculator",
            "crypto-tax-calculator",
            "age-calculator",
            "bmi-calculator",
            "fuel-cost-calculator",
            "salary-calculator",
            "gst-calculator",
            "invoice-generator",
            "word-counter",
            # Batch 2 (2026-10-10): high-traffic tools
            "qr-generator",
            "sip-calculator",
            "password-generator",
            "seo-writing-assistant",
            "meme-generator",
            "quotation-generator",
            "percentage-calculator",
            "uuid-generator",
            "json-formatter-validator",
            "image-compressor",
            "calculator",
            "mrr-calculator",
            # Batch 3: finance winners + viral + flagship tools
            "mortgage-overpayment-calculator",
            "adsense-calculator",
            "fd-calculator",
            "love-calculator",
            "image-background-remover",
            "crypto-price-prediction",
            "paraphrasing-tool",
            "resume-generator",
            "pdf-merger",
            "expense-tracker",
            "compound-calculator",
            "freelance-rate-calculator",
            # Batch 4: retirement/creator/image/dev/utility
            "retirement-planning-calculator",
            "youtube-calculator",
            "instagram-calculator",
            "image-converter",
            "image-resizer-cropper",
            "image-exif-remover",
            "base64-tool",
            "regex-tester",
            "meta-tag-generator",
            "unit-converter",
            "date-calculator",
            "text-case-converter",
            # Batch 5: crypto + CSS + doc generators
            "crypto-dca-calculator",
            "crypto-mining-calculator",
            "crypto-profit-calculator",
            "crypto-portfolio-analyzer",
            "crypto-fear-greed-index-tracker",
            "css-gradient-generator",
            "css-box-shadow-generator",
            "css-animation-generator",
            "purchase-order-generator",
            "sales-order-generator",
            "service-order-generator",
            "work-order-generator",
        ]
        all_tools = ToolDataLoader.get_all()
        for slug in pilots:
            i18n = all_tools[slug].get("i18n") or {}
            for loc in ("hi", "es", "fr"):
                assert loc in i18n, f"{slug} missing {loc}"
                assert len(i18n[loc].get("keywords", [])) <= 8

    def test_all_i18n_overrides_meet_length_guards(self, settings):
        """Lock SEO length/cap rules for every locale override (present + future batches)."""
        from app.core.tool_data import ToolDataLoader

        all_tools = ToolDataLoader.get_all()
        checked = 0
        pilot_slugs = set()
        for slug, info in all_tools.items():
            for loc in ("hi", "es", "fr"):
                over = (info.get("i18n") or {}).get(loc) or {}
                if not over:
                    continue
                checked += 1
                if loc == "hi":
                    pilot_slugs.add(slug)
                assert over.get("meta_title") and len(over["meta_title"]) <= 70, f"{slug}/{loc} title"
                assert over.get("description") and 120 <= len(over["description"]) <= 200, f"{slug}/{loc} desc"
                assert len(over.get("keywords", [])) <= 8, f"{slug}/{loc} kws"
                assert len(over.get("faqs", [])) >= 3, f"{slug}/{loc} faqs"
        # Dynamic floor: every hi pilot x 3 locales (no hardcoded 58).
        assert checked >= len(pilot_slugs) * 3, f"expected {len(pilot_slugs)} x 3, got {checked}"
        assert pilot_slugs, "no hi pilots found"

    def test_pilot_locales_symmetric(self, settings):
        """Every tool with a hi override must have es+fr too (no half-translated set)."""
        from app.core.tool_data import ToolDataLoader

        all_tools = ToolDataLoader.get_all()
        bad = [
            slug
            for slug, info in all_tools.items()
            if (info.get("i18n") or {}).get("hi")
            and not ((info.get("i18n") or {}).get("es") and (info.get("i18n") or {}).get("fr"))
        ]
        assert not bad, f"asymmetric pilots: {bad[:10]}"

    def test_tool_fallback_en(self, settings):
        from fastapi.testclient import TestClient

        from app.services.seo_service import SeoService

        # task-manager is a true non-pilot (no i18n overrides at all)
        svc2 = SeoService(settings)
        hi = svc2.get_seo("task-manager", locale="hi")
        en = svc2.get_seo("task-manager", locale="en")
        # non-pilot falls back to EN content but keeps locale + localized URL
        assert hi.locale == "hi"
        assert hi.url.endswith("/hi/tool/task-manager")
        assert hi.name == en.name
        assert hi.description == en.description
        # HTTP: fallback is noindex + filtered hreflang (EN + x-default only)
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/hi/tool/task-manager")
        assert r.status_code == 200
        assert r.headers.get("Content-Language") == "hi"
        assert r.headers.get("X-Robots-Tag") == "noindex, nofollow"
        # Fallback emits zero hreflang (suppressed with noindex by design)
        assert 'hreflang="hi"' not in r.text
        assert 'hreflang="en"' not in r.text
        assert 'hreflang="x-default"' not in r.text

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

    def test_locale_keywords_unique_within_and_vs_blog(self, settings):
        """No exact dup keyword across two tools, or tool-vs-blog, within one locale."""
        import yaml

        from app.core.tool_data import ToolDataLoader

        all_tools = ToolDataLoader.get_all()
        with open("data/blog.yaml", encoding="utf-8") as f:
            posts = yaml.safe_load(f)["posts"]
        for loc in ("hi", "es", "fr"):
            seen: dict[str, str] = {}
            for slug, info in all_tools.items():
                over = (info.get("i18n") or {}).get(loc) or {}
                for k in over.get("keywords", []) or []:
                    key = str(k).strip().lower()
                    assert key not in seen, f"{loc} dup: {key!r} in {slug} + {seen[key]}"
                    seen[key] = f"tool:{slug}"
            for slug, info in posts.items():
                over = (info.get("i18n") or {}).get(loc) or {}
                for k in over.get("keywords", []) or []:
                    key = str(k).strip().lower()
                    assert key not in seen, f"{loc} tool/blog overlap: {key!r} in blog:{slug} + {seen[key]}"
                    seen[key] = f"blog:{slug}"

    def test_blog_i18n_bodies_sane(self, settings):
        """Translated post bodies: substantial, one tool link, no H2/tables; faqs 3-10."""
        import re

        import yaml

        with open("data/blog.yaml", encoding="utf-8") as f:
            posts = yaml.safe_load(f)["posts"]
        checked = 0
        for slug, info in posts.items():
            for loc in ("hi", "es", "fr"):
                over = (info.get("i18n") or {}).get(loc) or {}
                if not over:
                    continue
                checked += 1
                body = str(over.get("body_html", ""))
                assert len(body) >= 1500, f"{slug}/{loc} thin body {len(body)}"
                assert 'href="/tool/' in body, f"{slug}/{loc} no tool link"
                assert "<h2" not in body.lower(), f"{slug}/{loc} H2 in body"
                assert "<table" not in body.lower(), f"{slug}/{loc} table in body"
                assert 3 <= len(over.get("faqs", [])) <= 10, f"{slug}/{loc} faqs"
                assert all(re.search(r"\w", str(f.get("q", ""))) for f in over.get("faqs", [])), f"{slug}/{loc} empty q"
        expected = sum(1 for _s, _i in posts.items() for _l in ("hi", "es", "fr") if (_i.get("i18n") or {}).get(_l))
        assert checked == expected and checked >= 15, f"expected {expected}, got {checked}"


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
        # Translated tool carries the full cluster + self markers, no noindex
        for code in ("en", "hi", "es", "fr"):
            assert f'hreflang="{code}"' in r.text, code
        assert '<html lang="hi"' in r.text
        assert "Vary" in r.headers and "Accept-Language" in r.headers["Vary"]
        assert "X-Robots-Tag" not in r.headers
        assert "og:locale" in r.text and "hi_IN" in r.text
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
        assert c.get("/xx/").status_code == 404
        assert c.get("/xx/blog").status_code == 404
        assert c.get("/xx/blog/calculators").status_code == 404

    def test_locale_case_and_slash_routing(self):
        """Uppercase locale 308s to lowercase; bare/trailing variants pinned."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        r = c.get("/HI/tool/emi-calculator", follow_redirects=False)
        assert r.status_code == 308, r.status_code
        assert r.headers["location"].endswith("/hi/tool/emi-calculator")
        # Bare locale homes render
        for loc in ("hi", "es", "fr"):
            rb = c.get(f"/{loc}")
            assert rb.status_code == 200, loc
            assert rb.headers.get("Content-Language") == loc
        # Trailing-slash on sub-pages redirects (Starlette slash redirect)
        rt = c.get("/hi/tools/", follow_redirects=False)
        assert rt.status_code in (301, 307, 308), rt.status_code

    def test_directory_offline_sitemap_locale(self):
        """/{loc}/directory 301s; /{loc}/offline + /{loc}/sitemap render localized."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        for loc in ("hi", "es", "fr"):
            d = c.get(f"/{loc}/directory", follow_redirects=False)
            assert d.status_code == 301, (loc, d.status_code)
            assert d.headers["location"] == f"/{loc}/tools"
            o = c.get(f"/{loc}/offline")
            assert o.status_code == 200, (loc, o.status_code)
            assert o.headers.get("Content-Language") == loc
            s = c.get(f"/{loc}/sitemap")
            assert s.status_code == 200, (loc, s.status_code)
            assert s.headers.get("Content-Language") == loc
            assert f"/{loc}/tool/" in s.text

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
        # EN sitemap alias redirects; unknown locale 404s
        re_ = c.get("/sitemap-en.xml", follow_redirects=False)
        assert re_.status_code == 301, re_.status_code
        assert re_.headers["location"] == "/sitemap.xml"
        assert c.get("/sitemap-xx.xml").status_code == 404
        # Fallback (untranslated) tools excluded from locale sitemaps
        assert "/hi/tool/task-manager" not in r.text
        assert "/hi/tool/emi-calculator" in r.text
        assert r.headers.get("Content-Language") == "hi"

    def test_language_switcher_present(self):
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        # Deep-link preservation per template
        for path, suffix in (
            ("/tool/emi-calculator", "/tool/emi-calculator"),
            ("/hi/tool/emi-calculator", "/tool/emi-calculator"),
            ("/es/tool/emi-calculator", "/tool/emi-calculator"),
            ("/hi/blog/calculators/emi-calculator-guide", "/blog/calculators/emi-calculator-guide"),
        ):
            r = c.get(path)
            assert r.status_code == 200, path
            for code in ("hi", "es", "fr"):
                assert f"/{code}{suffix}" in r.text, (path, code)
            assert 'aria-current="page"' in r.text
        # Home switcher keeps all locales reachable
        rh = c.get("/hi/")
        assert rh.status_code == 200
        for code in ("hi", "es", "fr"):
            assert f"/{code}/" in rh.text, code

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
        fr = c.get("/api/tools/catalog?lang=fr")
        assert any(t["url"].startswith("/fr/tool/") for t in fr.json())
        assert fr.headers.get("Content-Language") == "fr"
        # Uppercase lang normalizes; missing lang defaults to EN
        hi_upper = c.get("/api/tools/catalog?lang=HI")
        assert hi_upper.headers.get("Content-Language") == "hi"
        assert hi_upper.json() == hi.json()
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
        # Localized utility pages render with locale context
        for loc in ("hi", "es", "fr"):
            ro = c.get(f"/{loc}/offline")
            assert ro.status_code == 200, loc
            assert ro.headers.get("Content-Language") == loc
            rs = c.get(f"/{loc}/sitemap")
            assert rs.status_code == 200, loc
            assert rs.headers.get("Content-Language") == loc

    def test_blog_post_etag_per_locale(self):
        """Post ETags are locale-scoped: EN ETag must not 304 a locale URL."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        en = c.get("/blog/calculators/emi-calculator-guide")
        hi = c.get("/hi/blog/calculators/emi-calculator-guide")
        assert en.status_code == 200 and hi.status_code == 200
        etag_en = en.headers.get("ETag", "")
        etag_hi = hi.headers.get("ETag", "")
        assert etag_en and etag_hi and etag_en != etag_hi
        # Cross-locale ETag must NOT satisfy; same-locale must 304
        r_cross = c.get("/hi/blog/calculators/emi-calculator-guide", headers={"If-None-Match": etag_en})
        assert r_cross.status_code == 200, r_cross.status_code
        r_same = c.get("/hi/blog/calculators/emi-calculator-guide", headers={"If-None-Match": etag_hi})
        assert r_same.status_code == 304, r_same.status_code
        assert r_same.headers.get("Content-Language") == "hi"

    def test_blog_fallback_locale_noindex(self):
        """Untranslated post under /hi/ is usable but noindex with empty hreflang."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        # dark-mode-favicon-svg-guide has no hi override
        r = c.get("/hi/blog/developer-seo/dark-mode-favicon-svg-guide")
        assert r.status_code == 200, r.status_code
        assert r.headers.get("Content-Language") == "hi"
        assert r.headers.get("X-Robots-Tag") == "noindex, nofollow"
        assert 'hreflang="hi"' not in r.text

    def test_blog_index_localized(self):
        """Regression: /hi|es|fr/blog must render (prod 404 report, 2026-10-10)."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        for loc in ("hi", "es", "fr"):
            r = c.get(f"/{loc}/blog")
            assert r.status_code == 200, loc
            assert "text/html" in r.headers.get("content-type", "")
            assert r.headers.get("Content-Language") == loc
            assert f"/{loc}/blog/" in r.text or f"/{loc}/blog" in r.text

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

    def test_sitemap_urls_for_normalization(self):
        from scripts.submit_indexnow import sitemap_urls_for

        # Uppercase + duplicates collapse to one entry per valid locale
        urls = sitemap_urls_for("www.storybrainai.com", include_all=False, locales=["HI", "es", "xx", "es"])
        assert urls == [
            "https://www.storybrainai.com/sitemap-hi.xml",
            "https://www.storybrainai.com/sitemap-es.xml",
        ]

    def test_contact_from_locale_page(self):
        """Contact POST with locale Referer passes origin check; page is noindexed."""
        from app.main import app

        c = TestClient(app, base_url="http://127.0.0.1")
        page = c.get("/hi/contact")
        assert page.status_code == 200
        assert page.headers.get("Content-Language") == "hi"
        assert page.headers.get("X-Robots-Tag") == "noindex, nofollow"
        r = c.post(
            "/api/contact",
            json={"name": "Asha", "email": "asha@example.com", "message": "Namaste from Hindi page"},
            headers={"Origin": "http://127.0.0.1", "Referer": "http://127.0.0.1/hi/contact"},
        )
        assert r.status_code == 200, r.text
