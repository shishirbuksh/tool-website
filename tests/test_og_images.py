"""Per-tool / per-post OG images: files exist, valid 1200x630 WebP, wired into pages."""

import os
from tests.conftest import DjangoTestClientWrapper
from apps.core.config import settings


def _slugs():
    from apps.catalog.services import ToolDataLoader

    return sorted(ToolDataLoader.get_all().keys())


def _post_slugs():
    from apps.blog.services import BlogService

    return sorted(p.slug for p in BlogService(settings).get_all())


def test_tool_og_files_exist():
    from apps.catalog.services import ToolDataLoader

    missing = []
    for slug in ToolDataLoader.get_all():
        p = os.path.join(settings.static_dir, "og", "t", f"{slug}.webp")
        if not os.path.isfile(p):
            missing.append(slug)
    assert not missing, f"missing tool OG images: {missing[:10]}"


def test_post_og_files_exist():
    for slug in _post_slugs():
        p = os.path.join(settings.static_dir, "og", "p", f"{slug}.webp")
        assert os.path.isfile(p), f"missing post OG image: {slug}"


def test_og_files_valid_webp_1200x630():
    from PIL import Image

    bad = []
    for sub in ("t", "p"):
        d = os.path.join(settings.static_dir, "og", sub)
        for fname in sorted(os.listdir(d)):
            if not fname.endswith(".webp"):
                continue
            with Image.open(os.path.join(d, fname)) as im:
                if im.size != (1200, 630):
                    bad.append(f"{sub}/{fname}:{im.size}")
    assert not bad, f"bad dimensions: {bad[:5]}"


def test_og_bundle_under_12mb():
    total = 0
    for sub in ("t", "p"):
        d = os.path.join(settings.static_dir, "og", sub)
        for fname in os.listdir(d):
            total += os.path.getsize(os.path.join(d, fname))
    assert total < 12 * 1024 * 1024, f"OG bundle too big: {total} bytes"


def test_tool_page_uses_per_tool_og():
    c = DjangoTestClientWrapper()
    r = c.get("/tool/emi-calculator")
    assert r.status_code == 200
    assert "/static/og/t/emi-calculator.webp" in r.text
    img = c.get("/static/og/t/emi-calculator.webp")
    assert img.status_code == 200, img.status_code


def test_post_page_uses_per_post_og():
    c = DjangoTestClientWrapper()
    r = c.get("/blog/calculators/emi-calculator-guide")
    assert r.status_code == 200
    assert "/static/og/p/emi-calculator-guide.webp" in r.text


def test_seo_service_prefers_per_tool_og():
    from apps.catalog.services import SeoService

    svc = SeoService(settings)
    seo = svc.get_seo("emi-calculator", locale="en")
    assert seo.image_url == "/static/og/t/emi-calculator.webp", seo.image_url


def test_blog_service_prefers_per_post_og():
    from apps.blog.services import BlogService

    svc = BlogService(settings)
    post = svc.get("emi-calculator-guide", locale="en")
    assert post is not None
    assert post.image == "/static/og/p/emi-calculator-guide.webp", post.image
