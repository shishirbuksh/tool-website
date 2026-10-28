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

``--all-locales`` (and explicit ``--locale`` sitemaps) only submit locales that
are currently released in ``data/locale_publication.yaml``. Quarantined locale
sitemaps and explicit ``--url`` values under those locales are skipped; submit
English or released-locale URLs instead.

Docs: https://www.indexnow.org/documentation
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

API_ENDPOINT = "https://api.indexnow.org/IndexNow"
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
KEY_RE = re.compile(r"^[0-9a-fA-F]{8,128}$")
CHUNK = 10_000
# Subdirectory locales (must match app/core/i18n.py SUPPORTED_LOCALES minus "en").
I18N_LOCALES = ("hi", "es", "fr", "de")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def released_i18n_locales() -> list[str]:
    """Locales currently released for indexing, from the central policy.

    Fail closed: if the policy cannot be loaded, no locale sitemap is submitted.
    """
    try:
        from app.core.locale_policy import published_locales

        return [loc for loc in published_locales() if loc in I18N_LOCALES]
    except Exception as exc:  # pragma: no cover - defensive for standalone runs
        print(f"warning: cannot read locale release policy: {exc}", file=sys.stderr)
        return []


def url_locale(url: str) -> str:
    """Return the subdirectory locale of a URL (``en`` when prefix-less)."""
    path = urllib.parse.urlparse(url).path
    first = path.strip("/").split("/", 1)[0].lower()
    return first if first in I18N_LOCALES else "en"


def sitemap_urls_for(host: str, *, include_all: bool, locales: list[str]) -> list[str]:
    """Sitemap.xml URLs to fetch for IndexNow submission (testable, no I/O)."""
    urls: list[str] = []
    if include_all:
        urls.append(f"https://{host}/sitemap.xml")
    seen: set[str] = set()
    for loc in locales:
        loc = (loc or "").strip().lower()
        if loc in I18N_LOCALES and loc not in seen:
            seen.add(loc)
            urls.append(f"https://{host}/sitemap-{loc}.xml")
    return urls


def fetch_sitemap_locs(sitemap_url: str, timeout: int, _depth: int = 0) -> list[str]:
    req = urllib.request.Request(sitemap_url, headers={"User-Agent": "StoryBrainAI-IndexNow/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        xml = resp.read().decode("utf-8", errors="replace")
    locs = LOC_RE.findall(xml)
    # Recurse one level into sitemap indexes (e.g. sitemap-index.xml lists
    # sitemap-hi/es/fr.xml); page <loc>s are returned as-is. Depth-capped.
    if _depth < 1 and ("<sitemapindex" in xml or "sitemapindex" in xml[:2000]):
        nested: list[str] = []
        for loc in locs:
            if loc.strip().lower().endswith(".xml"):
                try:
                    nested += fetch_sitemap_locs(loc.strip(), timeout, _depth + 1)
                except OSError as e:
                    print(f"skip nested sitemap {loc}: {e}", file=sys.stderr)
        return nested
    return locs


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
    ap.add_argument(
        "--host", default="www.storybrainai.com", help="Bare host, no scheme (default: www.storybrainai.com)"
    )
    ap.add_argument("--url", action="append", dest="urls", default=[], help="URL to submit (repeatable)")
    ap.add_argument("--url-file", help="File with one URL per line")
    ap.add_argument("--sitemap-url", help="Fetch URLs from a sitemap.xml URL")
    ap.add_argument("--all", action="store_true", help="Submit every URL in the live sitemap.xml")
    ap.add_argument(
        "--locale",
        action="append",
        dest="locales",
        default=[],
        help="Also submit a locale sitemap (hi/es/fr/de; repeatable)",
    )
    ap.add_argument("--all-locales", action="store_true", help="Submit all locale sitemaps (sitemap-hi/es/fr/de.xml) too")
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if not KEY_RE.fullmatch(args.key or ""):
        print(
            'error: --key must be 8-128 hex chars (generate: python3 -c "import secrets; print(secrets.token_hex(16))")',
            file=sys.stderr,
        )
        return 2

    urls: list[str] = list(args.urls)
    if args.url_file:
        with open(args.url_file, encoding="utf-8") as f:
            urls += [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
    locales = list(args.locales)
    if args.all_locales:
        locales += [loc for loc in I18N_LOCALES if loc not in locales]

    # Never push a quarantined locale's sitemap: IndexNow would advertise URLs
    # that the app deliberately serves noindex. Explicit URLs under a
    # quarantined locale are skipped for the same reason.
    released = set(released_i18n_locales())
    blocked = [loc for loc in locales if (loc or "").strip().lower() not in released]
    if blocked:
        print(f"skip quarantined locale sitemap(s): {', '.join(blocked)}", file=sys.stderr)
    locales = [loc for loc in locales if (loc or "").strip().lower() in released]

    for sitemap in sitemap_urls_for(args.host, include_all=args.all, locales=locales):
        urls += fetch_sitemap_locs(sitemap, args.timeout)
    sitemap = args.sitemap_url
    if sitemap:
        urls += fetch_sitemap_locs(sitemap, args.timeout)

    # De-dupe, keep order; drop non-http(s) and off-host URLs (IndexNow spec:
    # every submitted URL's host must match `host`).
    seen: set[str] = set()
    clean: list[str] = []
    for u in urls:
        u = u.strip()
        if not u or u in seen:
            continue
        if not u.startswith(("http://", "https://")):
            print(f"skip non-URL: {u}", file=sys.stderr)
            continue
        try:
            netloc = urllib.parse.urlparse(u).hostname or ""
        except ValueError:
            netloc = ""
        if netloc.lower() != args.host.lower():
            print(f"skip off-host URL: {u}", file=sys.stderr)
            continue
        loc = url_locale(u)
        if loc != "en" and loc not in released:
            print(f"skip quarantined locale URL: {u}", file=sys.stderr)
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
            post_chunk(
                key=args.key,
                host=args.host,
                key_location=key_location,
                urls=clean[i : i + CHUNK],
                timeout=args.timeout,
                dry_run=args.dry_run,
            )
        )
    print(f"done: chunks={len(statuses)} statuses={statuses}")
    return 0 if all(s in (200, 202) for s in statuses) else 1


if __name__ == "__main__":
    raise SystemExit(main())
