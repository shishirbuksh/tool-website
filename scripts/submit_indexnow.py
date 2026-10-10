#!/usr/bin/env python3
"""Submit URLs to search engines via the IndexNow protocol (Bing, Yandex, Naver, Seznam).

Reads URLs from args, a file, or --sitemap-url (defaults to the live sitemap),
then POSTs them in chunks to the IndexNow endpoint.

Setup (one time):
  1. Generate a key:  python3 -c "import secrets; print(secrets.token_hex(16))"
  2. Set INDEXNOW_KEY=<key> in .env and deploy (app serves /<KEY>.txt automatically).
  3. Register the key in Bing Webmaster Tools if prompted.

Usage:
  python3 scripts/submit_indexnow.py --key <KEY> --url https://www.storybrainai.com/tool/calculator
  python3 scripts/submit_indexnow.py --key <KEY> --all
  python3 scripts/submit_indexnow.py --key <KEY> --all --dry-run
  python3 scripts/submit_indexnow.py --key <KEY> --all --all-locales --dry-run
  python3 scripts/submit_indexnow.py --key <KEY> --locale hi --locale es
  python3 scripts/submit_indexnow.py --key <KEY> --sitemap-url https://www.storybrainai.com/sitemap.xml

Docs: https://www.indexnow.org/documentation
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request

API_ENDPOINT = "https://api.indexnow.org/IndexNow"
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
CHUNK = 10_000
# Subdirectory locales (must match app/core/i18n.py SUPPORTED_LOCALES minus "en").
I18N_LOCALES = ("hi", "es", "fr")


def sitemap_urls_for(host: str, *, include_all: bool, locales: list[str]) -> list[str]:
    """Sitemap.xml URLs to fetch for IndexNow submission (testable, no I/O)."""
    urls: list[str] = []
    if include_all:
        urls.append(f"https://{host}/sitemap.xml")
    for loc in locales:
        if loc in I18N_LOCALES:
            urls.append(f"https://{host}/sitemap-{loc}.xml")
    return urls


def fetch_sitemap_locs(sitemap_url: str, timeout: int) -> list[str]:
    req = urllib.request.Request(sitemap_url, headers={"User-Agent": "StoryBrainAI-IndexNow/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        xml = resp.read().decode("utf-8", errors="replace")
    return LOC_RE.findall(xml)


def post_chunk(*, key: str, host: str, key_location: str, urls: list[str], timeout: int, dry_run: bool) -> int:
    payload = {"host": host, "key": key, "keyLocation": key_location, "urlList": urls}
    body = json.dumps(payload).encode("utf-8")
    if dry_run:
        print(f"DRY-RUN chunk: {len(urls)} urls (first: {urls[0]})")
        return 200
    req = urllib.request.Request(
        API_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": "StoryBrainAI-IndexNow/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} for chunk of {len(urls)} urls: {e.read()[:200]!r}", file=sys.stderr)
        return e.code
    except OSError as e:
        print(f"Network error submitting {len(urls)} urls: {e}", file=sys.stderr)
        return -1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Submit URLs via IndexNow.")
    ap.add_argument("--key", required=True, help="IndexNow key (must match INDEXNOW_KEY in .env)")
    ap.add_argument("--host", default="www.storybrainai.com", help="Bare host, no scheme (default: www.storybrainai.com)")
    ap.add_argument("--url", action="append", dest="urls", default=[], help="URL to submit (repeatable)")
    ap.add_argument("--url-file", help="File with one URL per line")
    ap.add_argument("--sitemap-url", help="Fetch URLs from a sitemap.xml URL")
    ap.add_argument("--all", action="store_true", help="Submit every URL in the live sitemap.xml")
    ap.add_argument("--locale", action="append", dest="locales", default=[],
                    help="Also submit a locale sitemap (hi/es/fr; repeatable)")
    ap.add_argument("--all-locales", action="store_true",
                    help="Submit all locale sitemaps (sitemap-hi/es/fr.xml) too")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    urls: list[str] = list(args.urls)
    if args.url_file:
        with open(args.url_file, encoding="utf-8") as f:
            urls += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    locales = list(args.locales)
    if args.all_locales:
        locales += [loc for loc in I18N_LOCALES if loc not in locales]
    for sitemap in sitemap_urls_for(args.host, include_all=args.all, locales=locales):
        urls += fetch_sitemap_locs(sitemap, args.timeout)
    sitemap = args.sitemap_url
    if sitemap:
        urls += fetch_sitemap_locs(sitemap, args.timeout)

    # De-dupe, keep order; drop non-http(s) and off-host URLs.
    seen: set[str] = set()
    clean: list[str] = []
    for u in urls:
        u = u.strip()
        if not u or u in seen:
            continue
        if not u.startswith(("http://", "https://")):
            print(f"skip non-URL: {u}", file=sys.stderr)
            continue
        seen.add(u)
        clean.append(u)
    if not clean:
        print("no URLs to submit", file=sys.stderr)
        return 2

    key_location = f"https://{args.host}/{args.key}.txt"
    print(f"submitting {len(clean)} URL(s) for host {args.host} (keyLocation {key_location})")
    statuses = []
    for i in range(0, len(clean), CHUNK):
        statuses.append(
            post_chunk(key=args.key, host=args.host, key_location=key_location,
                       urls=clean[i:i + CHUNK], timeout=args.timeout, dry_run=args.dry_run)
        )
    print(f"done: chunks={len(statuses)} statuses={statuses}")
    return 0 if all(s in (200, 202) for s in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
