"""Download Inter & Outfit woff2 from Google Fonts and generate local @font-face CSS."""
import os
import re

import requests

BASE = "https://fonts.googleapis.com/css2"
FONTS = {
    "Inter": "wght@400;500;600;700",
    "Outfit": "wght@400;700;800",
}
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
FONTS_DIR = os.path.join(STATIC_DIR, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
css_parts = []

for family, weights in FONTS.items():
    url = f"{BASE}?family={family}:{weights}&display=swap"
    resp = requests.get(url, headers={"User-Agent": ua})
    css = resp.text

    for match in re.finditer(r"url\(([^)]+)\) format\('woff2'\)", css):
        font_url = match.group(1)
        fname = font_url.rsplit("/", 1)[-1].split("?")[0]
        local_path = os.path.join(FONTS_DIR, fname)
        if not os.path.exists(local_path):
            fr = requests.get(font_url, headers={"User-Agent": ua})
            with open(local_path, "wb") as f:
                f.write(fr.content)
            print(f"Downloaded {fname} ({len(fr.content)} bytes)")
        css = css.replace(font_url, f"/static/fonts/{fname}")

    css_parts.append(css)

full_css = "\n".join(css_parts)
css_path = os.path.join(STATIC_DIR, "css", "fonts.css")
with open(css_path, "w", encoding="utf-8") as f:
    f.write(full_css)
print(f"Wrote {css_path} ({len(full_css)} bytes)")
print(f"Font files in {FONTS_DIR}: {os.listdir(FONTS_DIR)}")
