#!/usr/bin/env python3
"""Locale backlog: one row per localized override with release blockers.

The quality gate answers "may this locale ship?". This report answers "what is
left to do?" for every ``i18n.<locale>`` block in ``data/tools.yaml`` and
``data/blog.yaml``. It reuses the gate's checks for depth, artifacts, language
signal and duplicate metadata, then adds the release-only fields that a
quarantined item is allowed to omit (status, reviewer, sources, ...).

Readiness values:
  released  item is indexable today (locale released + translation published)
  ready     no blockers, status published, but the locale itself is quarantined
  review    no blockers, status draft/review; needs native sign-off
  blocked   at least one release blocker remains
  missing   no localized override exists

Usage:
  python scripts/locale_backlog.py
  python scripts/locale_backlog.py --locale de --locale es
  python scripts/locale_backlog.py --csv var/locale-backlog.csv --json var/locale-backlog.json
  python scripts/locale_backlog.py --kind tool --slug emi-calculator

Exit codes: 0 = report written, 2 = bad input.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.core.i18n import normalize_locale  # noqa: E402
from app.core.locale_policy import published_locales, translation_decision  # noqa: E402
from scripts.quality_gate import (  # noqa: E402
    INDIA_ONLY_TOOLS,
    LOCALIZED,
    VALID_STATUSES,
    WESTERN_LOCALES,
    YMYL_HINTS,
    Issue,
    QualityGate,
    find_artifacts,
    html_to_text,
    word_count,
)

SCHEMA_VERSION = 1
LOCALE_ORDER = ("de", "es", "fr", "hi")
KINDS = ("tool", "blog")
FAQ_MIN = LOCALIZED.faq_error
FAQ_ANSWER_MIN = LOCALIZED.faq_answer_error
MISSING_FIELD_ORDER = (
    "translation_status",
    "name",
    "title",
    "meta_title",
    "description",
    "keywords",
    "about_body",
    "body_html",
    "faqs",
    "reviewer",
    "reviewed_at",
    "author",
    "sources",
)

_H2_RE = re.compile(r"<h2\b", re.IGNORECASE)
_LINK_RE = re.compile(r"<a\b[^>]*\bhref=[\"'](?:/|https?://(?:www\.)?storybrainai\.com)", re.IGNORECASE)

CSV_FIELDS = (
    "locale",
    "kind",
    "slug",
    "path",
    "status",
    "released_locale",
    "indexable",
    "readiness",
    "blockers",
    "warnings",
    "missing_fields",
    "word_count",
    "word_min",
    "faq_count",
    "faq_min",
    "short_faq_answers",
    "h2_count",
    "h2_min",
    "internal_links",
    "links_min",
    "keyword_count",
    "keywords_present",
    "artifacts",
    "ymyl",
    "reviewer",
    "reviewed_at",
    "author",
    "sources_count",
)


@dataclass(frozen=True)
class BacklogItem:
    locale: str
    kind: str
    slug: str
    path: str
    status: str
    released_locale: bool
    indexable: bool
    readiness: str
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    missing_fields: tuple[str, ...]
    word_count: int
    word_min: int
    faq_count: int
    faq_min: int
    short_faq_answers: int
    h2_count: int
    h2_min: int
    internal_links: int
    links_min: int
    keyword_count: int
    keywords_present: int
    artifacts: tuple[str, ...]
    ymyl: bool
    reviewer: str
    reviewed_at: str
    author: str
    sources_count: int


@dataclass
class BacklogReport:
    locales: list[str]
    items: list[BacklogItem]

    @property
    def totals(self) -> dict[str, Any]:
        by_readiness = Counter(item.readiness for item in self.items)
        by_locale = Counter(item.locale for item in self.items)
        by_status = Counter(item.status for item in self.items)
        by_kind = Counter(item.kind for item in self.items)
        by_locale_readiness: dict[str, dict[str, int]] = {}
        for loc in self.locales:
            counts = Counter(item.readiness for item in self.items if item.locale == loc)
            by_locale_readiness[loc] = dict(sorted(counts.items()))
        blockers = Counter(code for item in self.items for code in item.blockers)
        return {
            "items": len(self.items),
            "by_readiness": dict(sorted(by_readiness.items())),
            "by_locale": dict(sorted(by_locale.items())),
            "by_status": dict(sorted(by_status.items())),
            "by_kind": dict(sorted(by_kind.items())),
            "by_locale_readiness": by_locale_readiness,
            "top_blockers": dict(blockers.most_common(15)),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "locales": self.locales,
            "totals": self.totals,
            "items": [asdict(item) for item in self.items],
        }


def _is_ymyl(raw: dict[str, Any], slug: str) -> bool:
    haystack = f"{slug} {raw.get('category', '')} {raw.get('pillar', '')}".lower()
    return any(hint in haystack for hint in YMYL_HINTS)


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _artifact_codes(over: dict[str, Any]) -> list[str]:
    """Mirror the gate: hard artifacts anywhere, soft markers only in prose."""
    hard = {"replacement_char", "lsi_scaffold", "lorem_ipsum"}
    found = set(find_artifacts(over))
    prose = {key: value for key, value in over.items() if key not in ("body_html", "howto_steps", "howto_calculate")}
    soft = set(find_artifacts(prose)) - hard
    return sorted((found & hard) | (found & soft))


def _item_path(locale: str, kind: str, slug: str, raw: dict[str, Any]) -> str:
    if kind == "tool":
        return f"/{locale}/tool/{slug}"
    pillar = str(raw.get("pillar") or "").strip("/")
    return f"/{locale}/blog/{pillar}/{slug}"


def _classify(*, status: str, indexable: bool, blockers: list[str]) -> str:
    if "missing_translation" in blockers:
        return "missing"
    if blockers:
        return "blocked"
    if indexable:
        return "released"
    if status == "published":
        return "ready"
    return "review"


def _release_blockers(
    *,
    kind: str,
    slug: str,
    locale: str,
    over: dict[str, Any] | None,
    status: str,
    words: int,
    faqs: list[Any],
    short_answers: int,
    h2_count: int,
    internal_links: int,
    keywords_present: int,
    keyword_count: int,
    artifacts: list[str],
) -> list[str]:
    if not over:
        return ["missing_translation"]

    blockers: list[str] = []
    if not status or status == "missing":
        blockers.append("translation_status_missing")
    elif status not in VALID_STATUSES:
        blockers.append("invalid_translation_status")

    if not str(over.get("name") or over.get("title") or "").strip():
        blockers.append("missing_title")
    if not str(over.get("meta_title") or "").strip():
        blockers.append("missing_meta_title")
    if not str(over.get("description") or "").strip():
        blockers.append("missing_description")
    if keyword_count < 4:
        blockers.append("keyword_count")
    if not str((over.get("about_body") if kind == "tool" else over.get("body_html")) or "").strip():
        blockers.append("missing_body")
    if len(faqs) < FAQ_MIN:
        blockers.append("tool_faq_count" if kind == "tool" else "blog_faq_count")
    if short_answers:
        blockers.append("faq_answer_too_short")

    if not str(over.get("reviewer") or "").strip():
        blockers.append("missing_reviewer")
    if not _valid_date(over.get("reviewed_at")):
        blockers.append("missing_reviewed_at")
    if not str(over.get("author") or "").strip():
        blockers.append("missing_author")
    if not _strings(over.get("sources")):
        blockers.append("missing_sources")

    if kind == "tool":
        if words < LOCALIZED.tool_about_error:
            blockers.append("tool_about_too_thin")
    else:
        if words < LOCALIZED.blog_words_error:
            blockers.append("blog_body_too_thin")
        if h2_count < LOCALIZED.blog_h2_error:
            blockers.append("blog_h2_count")
        if internal_links < LOCALIZED.blog_links_error:
            blockers.append("blog_internal_links")

    blockers.extend(artifacts)
    if keyword_count and keywords_present == 0:
        blockers.append("keywords_absent")
    if status == "published" and over.get("noindex") is True:
        blockers.append("published_item_noindex")
    if status == "published" and kind == "tool" and slug in INDIA_ONLY_TOOLS and locale in WESTERN_LOCALES:
        blockers.append("india_only_tool_localized")
    return blockers


def _item_row(
    *,
    locale: str,
    kind: str,
    slug: str,
    raw: dict[str, Any],
    over: dict[str, Any] | None,
    issues: list[Issue],
    released: set[str],
) -> BacklogItem:
    over = over if isinstance(over, dict) and over else None
    status = str((over or {}).get("translation_status") or "").strip().lower()
    status = status or "missing"
    body = (over or {}).get("about_body") if kind == "tool" else (over or {}).get("body_html")
    words = word_count(body)
    faqs = (over or {}).get("faqs") or []
    faqs = faqs if isinstance(faqs, list) else []
    short_answers = sum(
        1 for faq in faqs if isinstance(faq, dict) and word_count(faq.get("a") or faq.get("answer")) < FAQ_ANSWER_MIN
    )
    h2_count = len(_H2_RE.findall(str((over or {}).get("body_html") or "")))
    internal_links = len(_LINK_RE.findall(str((over or {}).get("body_html") or "")))
    keywords = (over or {}).get("keywords") or []
    keywords = (
        [str(keyword).strip() for keyword in keywords if str(keyword).strip()] if isinstance(keywords, list) else []
    )
    haystack = html_to_text(
        " ".join(
            str((over or {}).get(field) or "")
            for field in ("name", "title", "meta_title", "description", "about_body", "body_html")
        )
    ).lower()
    keywords_present = sum(1 for keyword in keywords if keyword.lower() in haystack)
    artifacts = _artifact_codes(over) if over else []

    blockers = _release_blockers(
        kind=kind,
        slug=slug,
        locale=locale,
        over=over,
        status=status,
        words=words,
        faqs=faqs,
        short_answers=short_answers,
        h2_count=h2_count,
        internal_links=internal_links,
        keywords_present=keywords_present,
        keyword_count=len(keywords),
        artifacts=artifacts,
    )
    gate_errors = [issue.code for issue in issues if issue.severity == "error"]
    gate_warnings = [issue.code for issue in issues if issue.severity == "warning"]
    blockers = sorted(set(blockers) | set(gate_errors))
    warnings = sorted(set(gate_warnings) - set(blockers))

    missing_fields: list[str] = []
    if not status or status == "missing":
        missing_fields.append("translation_status")
    if not str((over or {}).get("name") or (over or {}).get("title") or "").strip():
        missing_fields.append("name" if kind == "tool" else "title")
    if not str((over or {}).get("meta_title") or "").strip():
        missing_fields.append("meta_title")
    if not str((over or {}).get("description") or "").strip():
        missing_fields.append("description")
    if not keywords:
        missing_fields.append("keywords")
    if not str(body or "").strip():
        missing_fields.append("about_body" if kind == "tool" else "body_html")
    if not faqs:
        missing_fields.append("faqs")
    if not str((over or {}).get("reviewer") or "").strip():
        missing_fields.append("reviewer")
    if not _valid_date((over or {}).get("reviewed_at")):
        missing_fields.append("reviewed_at")
    if not str((over or {}).get("author") or "").strip():
        missing_fields.append("author")
    if not _strings((over or {}).get("sources")):
        missing_fields.append("sources")

    indexable = translation_decision(over, locale).indexable
    readiness = _classify(status=status, indexable=indexable, blockers=blockers)

    return BacklogItem(
        locale=locale,
        kind=kind,
        slug=slug,
        path=_item_path(locale, kind, slug, raw),
        status=status,
        released_locale=locale in released,
        indexable=indexable,
        readiness=readiness,
        blockers=tuple(blockers),
        warnings=tuple(warnings),
        missing_fields=tuple(field for field in MISSING_FIELD_ORDER if field in missing_fields),
        word_count=words,
        word_min=LOCALIZED.tool_about_error if kind == "tool" else LOCALIZED.blog_words_error,
        faq_count=len(faqs),
        faq_min=FAQ_MIN,
        short_faq_answers=short_answers,
        h2_count=h2_count if kind == "blog" else 0,
        h2_min=LOCALIZED.blog_h2_error if kind == "blog" else 0,
        internal_links=internal_links if kind == "blog" else 0,
        links_min=LOCALIZED.blog_links_error if kind == "blog" else 0,
        keyword_count=len(keywords),
        keywords_present=keywords_present,
        artifacts=tuple(artifacts),
        ymyl=_is_ymyl(raw, slug),
        reviewer=str((over or {}).get("reviewer") or ""),
        reviewed_at=str((over or {}).get("reviewed_at") or ""),
        author=str((over or {}).get("author") or ""),
        sources_count=len(_strings((over or {}).get("sources"))),
    )


def build_backlog(
    locales: list[str],
    *,
    kinds: set[str] | None = None,
    slugs: set[str] | None = None,
) -> BacklogReport:
    """Audit every override for the selected locales using the release gate."""
    selected_kinds = kinds or set(KINDS)
    gate = QualityGate(
        locales=locales,
        statuses=set(VALID_STATUSES),
        slugs=slugs,
        check_sitemaps=False,
    )
    gate_report = gate.run()
    issues: dict[tuple[str, str, str], list[Issue]] = defaultdict(list)
    for issue in gate_report.issues:
        if issue.kind in KINDS and issue.slug != "-":
            issues[(issue.locale, issue.kind, issue.slug)].append(issue)

    released = set(published_locales())
    rows: list[BacklogItem] = []
    for locale in locales:
        for kind, items in (("tool", gate.tools), ("blog", gate.posts)):
            if kind not in selected_kinds:
                continue
            for slug, raw in sorted(items.items()):
                if slugs and slug not in slugs:
                    continue
                overrides = raw.get("i18n") or {}
                over = overrides.get(locale) if isinstance(overrides, dict) else None
                rows.append(
                    _item_row(
                        locale=locale,
                        kind=kind,
                        slug=slug,
                        raw=raw,
                        over=over if isinstance(over, dict) else None,
                        issues=issues.get((locale, kind, slug), []),
                        released=released,
                    )
                )
    return BacklogReport(locales=locales, items=rows)


def _csv_row(item: BacklogItem) -> dict[str, Any]:
    row = asdict(item)
    for key in ("blockers", "warnings", "missing_fields", "artifacts"):
        row[key] = ";".join(row[key])
    for key in ("released_locale", "indexable", "ymyl"):
        row[key] = "true" if row[key] else "false"
    return {field: row[field] for field in CSV_FIELDS}


def write_csv(path: Path, report: BacklogReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for item in report.items:
            writer.writerow(_csv_row(item))


def write_json(path: Path, report: BacklogReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def _selected_locales(values: list[str]) -> list[str]:
    if not values:
        return list(LOCALE_ORDER)
    selected = {normalize_locale(value) for value in values}
    unknown = [value for value in values if normalize_locale(value) != value.strip().lower()]
    if unknown:
        message = f"unknown locale(s): {', '.join(unknown)}"
        raise ValueError(message)
    if "en" in selected:
        raise ValueError("backlog covers non-English locales only")
    return [locale for locale in LOCALE_ORDER if locale in selected]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report localized content readiness and release blockers.")
    parser.add_argument("--locale", action="append", dest="locales", default=[], help="locale to audit (repeatable)")
    parser.add_argument("--kind", action="append", choices=KINDS, dest="kinds", default=[], help="content kind")
    parser.add_argument("--slug", action="append", dest="slugs", default=[], help="only audit these slugs")
    parser.add_argument("--csv", type=Path, help="write the item table as CSV (UTF-8 with BOM)")
    parser.add_argument("--json", type=Path, help="write the full report as JSON")
    parser.add_argument("--quiet", action="store_true", help="print totals only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        locales = _selected_locales(args.locales)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = build_backlog(
        locales,
        kinds=set(args.kinds) if args.kinds else None,
        slugs=set(args.slugs) if args.slugs else None,
    )
    totals = report.totals

    print(f"Locale backlog: {totals['items']} item(s), locales={','.join(locales)}")
    print(f"Readiness: {totals['by_readiness']}")
    if not args.quiet:
        print(f"By locale: {totals['by_locale_readiness']}")
        print(f"Top blockers: {totals['top_blockers']}")

    if args.csv:
        write_csv(args.csv, report)
        print(f"CSV: {args.csv}")
    if args.json:
        write_json(args.json, report)
        print(f"JSON: {args.json}")
    if not args.csv and not args.json and not args.quiet:
        print("No output file requested; use --csv and/or --json for the full table.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
