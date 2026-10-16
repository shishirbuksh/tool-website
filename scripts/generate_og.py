#!/usr/bin/env python3
"""Generate per-tool and per-post Open Graph images (1200x630 WebP).

Maintainer step (run when tools/posts are added/renamed; outputs committed):
    python3 scripts/generate_og.py [--force]

Design: dark navy base, per-category accent band + glow dot, bold title
(wrapped, up to 3 lines), footer brand line. Uses system Arial Bold if
available, else PIL's built-in bitmap font. Requires: pillow, pyyaml.
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap

try:
    import yaml
except ImportError:
    print("error: pyyaml required (pip install pyyaml)", file=sys.stderr)
    raise SystemExit(2) from None

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("error: pillow required (pip install pillow)", file=sys.stderr)
    raise SystemExit(2) from None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H = 1200, 630

ACCENTS = {
    "Calculators": (16, 185, 129),
    "AI & Crypto": (139, 92, 246),
    "Image Processing": (14, 165, 233),
    "Developer & SEO": (245, 158, 11),
    "Business & Operations": (59, 130, 246),
    "Productivity & Utilities": (244, 63, 94),
}
PILLAR_ACCENT = {
    "calculators": ACCENTS["Calculators"],
    "ai-crypto": ACCENTS["AI & Crypto"],
    "image-processing": ACCENTS["Image Processing"],
    "developer-seo": ACCENTS["Developer & SEO"],
    "business-operations": ACCENTS["Business & Operations"],
    "productivity-utilities": ACCENTS["Productivity & Utilities"],
}
DEFAULT_ACCENT = (14, 165, 233)

BG_TOP = (10, 15, 29)
BG_BOTTOM = (18, 28, 52)


def _load_font(size: int, bold: bool = True):
    candidates = (
        ["C:/Windows/Fonts/arialbd.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
        if bold
        else ["C:/Windows/Fonts/arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def render(title: str, accent: tuple[int, int, int], footer: str) -> Image.Image:
    # Vertical gradient via 1px-wide strip (fast) scaled up.
    strip = Image.new("RGB", (1, H))
    strip.putdata(
        [
            (
                _lerp(BG_TOP[0], BG_BOTTOM[0], y / (H - 1)),
                _lerp(BG_TOP[1], BG_BOTTOM[1], y / (H - 1)),
                _lerp(BG_TOP[2], BG_BOTTOM[2], y / (H - 1)),
            )
            for y in range(H)
        ]
    )
    img = strip.resize((W, H))
    d = ImageDraw.Draw(img, "RGBA")
    # Accent band + glow dot.
    d.rectangle([0, 0, 28, H], fill=accent)
    cx, cy, gr = 1010, 150, 260
    for r in range(gr, 0, -6):
        a = max(0, 40 - r // 8)
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (a,))
    d.ellipse([cx - 26, cy - 26, cx + 26, cy + 26], fill=accent)
    # Title: wrap + shrink-to-fit inside x∈[90,1050], max 3 lines.
    size = 84
    font = _load_font(size)
    lines = textwrap.wrap(title, width=24)
    while size > 36:
        widths = [d.textlength(line, font=font) for line in lines] or [0]
        if len(lines) <= 3 and max(widths) <= 950:
            break
        size -= 4
        font = _load_font(size)
        # Smaller font fits more chars per line: widen the wrap.
        lines = textwrap.wrap(title, width=max(24, int(24 * 84 / size)))
    lines = lines[:3]
    y = 200
    for line in lines:
        d.text((90, y), line, font=font, fill=(248, 250, 252))
        try:
            asc, desc = font.getmetrics()
            y += asc + desc + 8
        except AttributeError:
            y += size + 14
    # Footer brand line: accent brand + gray remainder, no overlap.
    brand = "StoryBrain AI"
    rest = footer[len(brand) :] if footer.startswith(brand) else footer
    brand_font = _load_font(34)
    foot_font = _load_font(34, bold=False)
    d.text((90, H - 110), brand, font=brand_font, fill=(56, 189, 248))
    try:
        bx = 90 + d.textlength(brand, font=brand_font)
    except AttributeError:
        bx = 90 + 300
    d.text((bx, H - 110), rest, font=foot_font, fill=(148, 163, 184))
    return img


def _load_yaml(name: str) -> dict:
    with open(os.path.join(BASE_DIR, "data", name), encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate per-page OG images.")
    ap.add_argument("--force", action="store_true", help="Regenerate even if output exists")
    ap.add_argument("--dry-run", action="store_true", help="List planned outputs without writing")
    args = ap.parse_args(argv)

    tools = _load_yaml("tools.yaml").get("tools", {})
    posts = _load_yaml("blog.yaml").get("posts", {})
    jobs: list[tuple[str, str, tuple[int, int, int], str]] = []
    for slug, info in sorted(tools.items()):
        jobs.append(
            (
                os.path.join(BASE_DIR, "static", "og", "t", f"{slug}.webp"),
                str(info.get("name", slug.replace("-", " ").title())),
                ACCENTS.get(str(info.get("category", "")), DEFAULT_ACCENT),
                "StoryBrain AI  •  Free Online Tool",
            )
        )
    for slug, info in sorted(posts.items()):
        jobs.append(
            (
                os.path.join(BASE_DIR, "static", "og", "p", f"{slug}.webp"),
                str(info.get("title", slug.replace("-", " ").title())),
                PILLAR_ACCENT.get(str(info.get("pillar", "")), DEFAULT_ACCENT),
                "StoryBrain AI  •  Free Guide",
            )
        )
    if args.dry_run:
        for out, *_ in jobs:
            print(out)
        print(f"planned: {len(jobs)} images")
        return 0
    made = skipped = 0
    total_bytes = 0
    for out, title, accent, footer in jobs:
        if os.path.exists(out) and not args.force:
            skipped += 1
            total_bytes += os.path.getsize(out)
            continue
        os.makedirs(os.path.dirname(out), exist_ok=True)
        render(title, accent, footer).save(out, "WEBP", quality=82, method=6)
        made += 1
        total_bytes += os.path.getsize(out)
    print(f"og images: {made} generated, {skipped} up-to-date, {len(jobs)} total, {total_bytes / 1048576:.1f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
