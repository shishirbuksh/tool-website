#!/usr/bin/env python3
"""Locale quality gate: block release of thin, unreviewed, or misconfigured translations.

The gate is intentionally stricter than the English baseline. A localized pack
must clear every check before ``data/locale_publication.yaml`` can mark its
locale ``published``; published items must also appear in the locale sitemap and
nowhere outside the indexable hreflang cluster.

Usage:
  python scripts/quality_gate.py                       # gate released locales (EN today)
  python scripts/quality_gate.py --all-locales         # audit quarantined locales too
  python scripts/quality_gate.py --locale de --slug emi-calculator
  python scripts/quality_gate.py --locale de --status published
  python scripts/quality_gate.py --all-locales --json > gate-report.json

Exit codes: 0 = pass, 1 = gate errors (or warnings with --strict), 2 = bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from html import unescape
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import yaml  # noqa: E402

LEGACY_LOCALE_PREFIXES = frozenset({"hi", "es", "fr", "de"})

VALID_STATUSES = frozenset({"draft", "review", "published"})
DEFAULT_STATUSES = ("published", "review")
YMYL_HINTS = (
    "loan",
    "emi",
    "mortgage",
    "credit",
    "tax",
    "salary",
    "bmi",
    "calorie",
    "pregnan",
    "investment",
    "crypto",
    "insurance",
    "interest",
    "sip",
    "fd",
    "retirement",
)

ARTIFACT_PATTERNS = (
    ("replacement_char", re.compile("\ufffd")),
    ("lsi_scaffold", re.compile(r"\bLSI\s*:", re.IGNORECASE)),
    ("todo_marker", re.compile(r"\b(?:TODO|FIXME|TBD)\s*:")),
    ("lorem_ipsum", re.compile(r"lorem ipsum", re.IGNORECASE)),
    ("template_placeholder", re.compile(r"\{\{|\}\}|\[insert|\[translate", re.IGNORECASE)),
)

_TAG_RE = re.compile(r"<[^>]+>")
_H2_RE = re.compile(r"<h2\b", re.IGNORECASE)
_H1_RE = re.compile(r"<h1\b", re.IGNORECASE)
_LINK_RE = re.compile(r"<a\b[^>]*\bhref=[\"'](?:/|https?://(?:www\.)?storybrainai\.com)", re.IGNORECASE)
_TOKEN_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_MULTISPACE_RE = re.compile(r"\s+")

EN_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "in",
        "for",
        "with",
        "that",
        "this",
        "you",
        "your",
        "on",
        "as",
        "be",
        "or",
        "at",
        "from",
        "by",
        "it",
        "an",
        "will",
        "can",
        "not",
        "have",
        "has",
        "had",
        "how",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
    }
)
TARGET_STOPWORDS: dict[str, frozenset[str]] = {
    "de": frozenset(
        {
            "der",
            "die",
            "das",
            "und",
            "ist",
            "sind",
            "mit",
            "für",
            "ein",
            "eine",
            "einen",
            "einem",
            "einer",
            "den",
            "dem",
            "des",
            "nicht",
            "auch",
            "als",
            "bei",
            "aus",
            "wird",
            "werden",
            "kann",
            "sie",
            "oder",
            "im",
            "in",
            "zu",
            "von",
            "auf",
            "sich",
            "dass",
            "es",
            "er",
            "wir",
            "ihr",
            "ihre",
            "unser",
            "unsere",
            "mehr",
            "sehr",
        }
    ),
    "es": frozenset(
        {
            "el",
            "la",
            "los",
            "las",
            "de",
            "del",
            "que",
            "y",
            "en",
            "un",
            "una",
            "unos",
            "unas",
            "es",
            "son",
            "con",
            "por",
            "para",
            "su",
            "sus",
            "como",
            "más",
            "pero",
            "o",
            "no",
            "este",
            "esta",
            "entre",
            "cuando",
            "muy",
            "sin",
            "sobre",
            "también",
            "hasta",
            "hay",
            "se",
            "al",
            "lo",
            "le",
            "les",
        }
    ),
    "fr": frozenset(
        {
            "le",
            "la",
            "les",
            "de",
            "des",
            "du",
            "un",
            "une",
            "et",
            "en",
            "est",
            "que",
            "qui",
            "dans",
            "pour",
            "avec",
            "sur",
            "pas",
            "au",
            "aux",
            "ce",
            "cette",
            "il",
            "elle",
            "sont",
            "plus",
            "par",
            "comme",
            "mais",
            "ou",
            "ne",
            "se",
            "son",
            "sa",
            "ses",
            "on",
            "nous",
            "vous",
            "leur",
            "leurs",
            "peut",
            "être",
            "aussi",
            "très",
        }
    ),
    "hi": frozenset(
        {
            "है",
            "हैं",
            "के",
            "में",
            "और",
            "से",
            "का",
            "की",
            "को",
            "पर",
            "यह",
            "वह",
            "एक",
            "नहीं",
            "भी",
            "हो",
            "कर",
            "लिए",
            "साथ",
            "या",
            "तो",
            "ही",
            "कि",
            "जो",
            "था",
            "थी",
        }
    ),
}


@dataclass(frozen=True)
class Thresholds:
    tool_about_error: int
    tool_about_warn: int
    faq_error: int
    faq_warn: int
    faq_answer_error: int
    faq_answer_warn: int
    blog_words_error: int
    blog_words_warn: int
    blog_h2_error: int
    blog_h2_warn: int
    blog_links_error: int
    blog_links_warn: int
    blog_faq_error: int


LOCALIZED = Thresholds(
    tool_about_error=150,
    tool_about_warn=250,
    faq_error=5,
    faq_warn=6,
    faq_answer_error=12,
    faq_answer_warn=20,
    blog_words_error=800,
    blog_words_warn=1100,
    blog_h2_error=4,
    blog_h2_warn=6,
    blog_links_error=4,
    blog_links_warn=8,
    blog_faq_error=5,
)
EN_BASELINE = Thresholds(
    tool_about_error=25,
    tool_about_warn=60,
    faq_error=4,
    faq_warn=5,
    faq_answer_error=8,
    faq_answer_warn=15,
    blog_words_error=500,
    blog_words_warn=900,
    blog_h2_error=3,
    blog_h2_warn=5,
    blog_links_error=2,
    blog_links_warn=4,
    blog_faq_error=4,
)


@dataclass(frozen=True)
class Issue:
    severity: str
    locale: str
    kind: str
    slug: str
    code: str
    message: str


@dataclass
class GateReport:
    locales: list[str]
    items_checked: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    @property
    def passed(self) -> bool:
        return not self.errors

    def add(self, severity: str, locale: str, kind: str, slug: str, code: str, message: str) -> None:
        self.issues.append(Issue(severity, locale, kind, slug, code, message))

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "locales": self.locales,
            "items_checked": self.items_checked,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors_by_code": dict(Counter(issue.code for issue in self.errors)),
            "warnings_by_code": dict(Counter(issue.code for issue in self.warnings)),
            "issues": [
                {
                    "severity": issue.severity,
                    "locale": issue.locale,
                    "kind": issue.kind,
                    "slug": issue.slug,
                    "code": issue.code,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }


def _load_yaml(path: Path) -> dict[str, Any]:
    stat = path.stat()
    loaded = _load_yaml_cached(str(path.resolve()), stat.st_mtime_ns, stat.st_size)
    return loaded


@lru_cache(maxsize=8)
def _load_yaml_cached(path: str, _mtime_ns: int, _size: int) -> dict[str, Any]:
    # libyaml is ~10x faster on these multi-megabyte content files. The mtime
    # and size arguments are cache-key only; the file is read once per change.
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    with open(path, encoding="utf-8") as handle:
        loaded = yaml.load(handle, Loader=loader) or {}
    return loaded if isinstance(loaded, dict) else {}


def html_to_text(value: Any) -> str:
    return _MULTISPACE_RE.sub(" ", unescape(_TAG_RE.sub(" ", str(value or "")))).strip()


def word_count(value: Any) -> int:
    return len(html_to_text(value).split())


def normalize_text(value: Any) -> str:
    return _MULTISPACE_RE.sub(" ", html_to_text(value).lower()).strip()


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)


def find_artifacts(value: Any) -> list[str]:
    """Return artifact codes found anywhere in a localized override."""
    found: list[str] = []
    for text in _iter_strings(value):
        for code, pattern in ARTIFACT_PATTERNS:
            if pattern.search(text) and code not in found:
                found.append(code)
    return found


def _is_ymyl(raw: dict[str, Any], slug: str) -> bool:
    haystack = f"{slug} {raw.get('category', '')} {raw.get('pillar', '')}".lower()
    return any(hint in haystack for hint in YMYL_HINTS)


def _valid_date(value: Any) -> bool:
    try:
        date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return False
    return True


def _keyword_coverage(keywords: list[Any], text: str) -> tuple[int, int]:
    haystack = text.lower()
    usable = [str(keyword).strip().lower() for keyword in keywords if len(str(keyword).strip()) >= 3]
    present = sum(1 for keyword in usable if keyword in haystack)
    return present, len(usable)


class QualityGate:
    def __init__(
        self,
        *,
        locales: list[str],
        statuses: set[str] | None = None,
        slugs: set[str] | None = None,
        check_sitemaps: bool = True,
    ) -> None:
        self.report = GateReport(locales=[str(loc).strip().lower() for loc in locales])
        self.statuses = statuses or set(DEFAULT_STATUSES)
        self.slugs = {slug.strip() for slug in slugs} if slugs else None
        self.check_sitemaps = check_sitemaps

        self.tools = _load_yaml(_REPO_ROOT / "data" / "tools.yaml").get("tools", {}) or {}
        self.posts = _load_yaml(_REPO_ROOT / "data" / "blog.yaml").get("posts", {}) or {}
        self.released = {"en"}

        self._bodies: dict[tuple[str, str, str], str] = {}
        self._meta_titles: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
        self._descriptions: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)

    def run(self) -> GateReport:
        self._check_en()
        self._check_duplicates()
        if self.check_sitemaps:
            self._check_sitemaps()
        return self.report

    # ------------------------------------------------------------------ items

    def _selected(self, slug: str) -> bool:
        return self.slugs is None or slug in self.slugs

    def _check_en(self) -> None:
        for slug, raw in sorted(self.tools.items()):
            if self._selected(slug):
                source = {key: value for key, value in raw.items() if key != "i18n"}
                self._check_tool("en", slug, raw, source)
        for slug, raw in sorted(self.posts.items()):
            if self._selected(slug):
                source = {key: value for key, value in raw.items() if key != "i18n"}
                self._check_blog("en", slug, raw, source)

    def _check_tool(self, loc: str, slug: str, raw: dict[str, Any], over: dict[str, Any]) -> None:
        self.report.items_checked += 1
        self._check_artifacts(loc, "tool", slug, over)
        self._check_common_metadata(loc, "tool", slug, over, require_meta=loc != "en")
        self._check_review_fields(loc, "tool", slug, raw, over)
        self._check_keywords(loc, "tool", slug, over)

        thresholds = LOCALIZED if loc != "en" else EN_BASELINE
        about_words = word_count(over.get("about_body"))
        if about_words < thresholds.tool_about_error:
            self.report.add(
                "error",
                loc,
                "tool",
                slug,
                "tool_about_too_thin",
                f"about_body has {about_words} words (min {thresholds.tool_about_error})",
            )
        elif about_words < thresholds.tool_about_warn:
            self.report.add(
                "warning",
                loc,
                "tool",
                slug,
                "tool_about_short",
                f"about_body has {about_words} words (target {thresholds.tool_about_warn}+)",
            )

        faqs = over.get("faqs") or []
        if not isinstance(faqs, list):
            faqs = []
        if len(faqs) < thresholds.faq_error:
            self.report.add(
                "error",
                loc,
                "tool",
                slug,
                "tool_faq_count",
                f"{len(faqs)} FAQs (min {thresholds.faq_error})",
            )
        elif len(faqs) < thresholds.faq_warn:
            self.report.add(
                "warning",
                loc,
                "tool",
                slug,
                "tool_faq_count_low",
                f"{len(faqs)} FAQs (target {thresholds.faq_warn}+)",
            )
        self._check_faqs(loc, "tool", slug, faqs, thresholds)

        if loc != "en":
            self._check_same_as_source(loc, "tool", slug, over.get("about_body"), raw.get("about_body"))
            self._check_language_signal(loc, "tool", slug, over.get("about_body"))
            self._check_primary_keyword_metadata(loc, "tool", slug, over, over.get("name"))
            self._remember_body(loc, "tool", slug, over.get("about_body"))

    def _check_blog(self, loc: str, slug: str, raw: dict[str, Any], over: dict[str, Any]) -> None:
        self.report.items_checked += 1
        self._check_artifacts(loc, "blog", slug, over)
        self._check_common_metadata(loc, "blog", slug, over, require_meta=loc != "en")
        self._check_review_fields(loc, "blog", slug, raw, over)
        self._check_keywords(loc, "blog", slug, over)

        thresholds = LOCALIZED if loc != "en" else EN_BASELINE
        body = str(over.get("body_html") or "")
        body_words = word_count(body)
        if body_words < thresholds.blog_words_error:
            self.report.add(
                "error",
                loc,
                "blog",
                slug,
                "blog_body_too_thin",
                f"body_html has {body_words} words (min {thresholds.blog_words_error})",
            )
        elif body_words < thresholds.blog_words_warn:
            self.report.add(
                "warning",
                loc,
                "blog",
                slug,
                "blog_body_short",
                f"body_html has {body_words} words (target {thresholds.blog_words_warn}+)",
            )

        h2_count = len(_H2_RE.findall(body))
        if h2_count < thresholds.blog_h2_error:
            self.report.add(
                "error",
                loc,
                "blog",
                slug,
                "blog_h2_count",
                f"{h2_count} H2 sections (min {thresholds.blog_h2_error})",
            )
        elif h2_count < thresholds.blog_h2_warn:
            self.report.add(
                "warning",
                loc,
                "blog",
                slug,
                "blog_h2_count_low",
                f"{h2_count} H2 sections (target {thresholds.blog_h2_warn}+)",
            )

        links = len(_LINK_RE.findall(body))
        if links < thresholds.blog_links_error:
            self.report.add(
                "error",
                loc,
                "blog",
                slug,
                "blog_internal_links",
                f"{links} internal links (min {thresholds.blog_links_error})",
            )
        elif links < thresholds.blog_links_warn:
            self.report.add(
                "warning",
                loc,
                "blog",
                slug,
                "blog_internal_links_low",
                f"{links} internal links (target {thresholds.blog_links_warn}+)",
            )

        if _H1_RE.search(body):
            self.report.add(
                "warning", loc, "blog", slug, "blog_body_h1", "body_html contains an <h1>; the template owns the H1"
            )

        faqs = over.get("faqs") or []
        if not isinstance(faqs, list):
            faqs = []
        if len(faqs) < thresholds.blog_faq_error:
            self.report.add(
                "error", loc, "blog", slug, "blog_faq_count", f"{len(faqs)} FAQs (min {thresholds.blog_faq_error})"
            )
        self._check_faqs(loc, "blog", slug, faqs, thresholds)

        if loc != "en":
            self._check_same_as_source(loc, "blog", slug, body, raw.get("body_html"))
            self._check_language_signal(loc, "blog", slug, body)
            self._check_primary_keyword_metadata(loc, "blog", slug, over, over.get("title"))
            self._remember_body(loc, "blog", slug, body)

    # ----------------------------------------------------------------- checks

    def _check_artifacts(self, loc: str, kind: str, slug: str, over: dict[str, Any]) -> None:
        # Hard artifacts are never legitimate, even inside a code sample.
        hard = {"replacement_char", "lsi_scaffold", "lorem_ipsum"}
        for code in find_artifacts(over):
            if code in hard:
                self.report.add("error", loc, kind, slug, code, f"localization artifact detected: {code}")
        # TODO markers / template braces are checked only in prose metadata:
        # blog code samples may legitimately contain both.
        prose = {key: value for key, value in over.items() if key not in ("body_html", "howto_steps", "howto_calculate")}
        for code in find_artifacts(prose):
            if code not in hard:
                self.report.add("error", loc, kind, slug, code, f"localization artifact detected: {code}")

    def _check_common_metadata(
        self, loc: str, kind: str, slug: str, over: dict[str, Any], *, require_meta: bool
    ) -> None:
        identity = over.get("name") or over.get("title")
        if not str(identity or "").strip():
            self.report.add("error", loc, kind, slug, "missing_title", "name/title is empty")

        meta_title = str(over.get("meta_title") or "").strip()
        if not meta_title:
            severity = "error" if require_meta else "warning"
            self.report.add(severity, loc, kind, slug, "missing_meta_title", "meta_title is empty")
        elif not 20 <= len(meta_title) <= 75:
            self.report.add(
                "warning",
                loc,
                kind,
                slug,
                "meta_title_length",
                f"meta_title is {len(meta_title)} chars (target 20-75)",
            )

        description = str(over.get("description") or "").strip()
        if not description:
            self.report.add("error", loc, kind, slug, "missing_description", "description is empty")
        elif len(description) < 70:
            self.report.add(
                "error",
                loc,
                kind,
                slug,
                "description_too_short",
                f"description is {len(description)} chars (min 70)",
            )
        elif len(description) > 180:
            self.report.add(
                "warning",
                loc,
                kind,
                slug,
                "description_too_long",
                f"description is {len(description)} chars (target <=180)",
            )

        key = (loc, kind)
        if meta_title:
            existing = self._meta_titles[key].get(meta_title.lower())
            if existing and existing != slug:
                self.report.add(
                    "error",
                    loc,
                    kind,
                    slug,
                    "duplicate_meta_title",
                    f"meta_title duplicates {existing}",
                )
            self._meta_titles[key][meta_title.lower()] = slug
        if description:
            existing = self._descriptions[key].get(description.lower())
            if existing and existing != slug:
                self.report.add(
                    "error",
                    loc,
                    kind,
                    slug,
                    "duplicate_description",
                    f"description duplicates {existing}",
                )
            self._descriptions[key][description.lower()] = slug

    def _check_review_fields(self, loc: str, kind: str, slug: str, raw: dict[str, Any], over: dict[str, Any]) -> None:
        if loc == "en":
            return
        status = str(over.get("translation_status") or "review").strip().lower()
        severity = "error" if status == "published" else "warning"

        if not str(over.get("reviewer") or "").strip():
            self.report.add(severity, loc, kind, slug, "missing_reviewer", "no native reviewer recorded")
        if not _valid_date(over.get("reviewed_at")):
            self.report.add(severity, loc, kind, slug, "missing_reviewed_at", "reviewed_at is missing/invalid (YYYY-MM-DD)")

        sources = over.get("sources")
        if not isinstance(sources, list) or not [source for source in sources if str(source).strip()]:
            source_severity = "error" if _is_ymyl(raw, slug) else "warning"
            self.report.add(source_severity, loc, kind, slug, "missing_sources", "no sources recorded for the pack")
        if not str(over.get("author") or "").strip():
            self.report.add("warning", loc, kind, slug, "missing_author", "no author recorded for the pack")

    def _check_keywords(self, loc: str, kind: str, slug: str, over: dict[str, Any]) -> None:
        keywords = over.get("keywords")
        if not isinstance(keywords, list):
            keywords = []
        keywords = [keyword for keyword in keywords if str(keyword).strip()]
        minimum = 3 if loc == "en" else 4
        if len(keywords) < minimum:
            self.report.add(
                "error" if loc != "en" else "warning",
                loc,
                kind,
                slug,
                "keyword_count",
                f"{len(keywords)} keywords (min {minimum})",
            )
            return
        text = " ".join(
            str(over.get(field) or "")
            for field in ("name", "title", "meta_title", "description", "about_body", "body_html")
        )
        present, usable = _keyword_coverage(keywords, html_to_text(text))
        if usable and present == 0:
            self.report.add(
                "error" if loc != "en" else "warning",
                loc,
                kind,
                slug,
                "keywords_absent",
                "none of the declared keywords appear in the localized copy",
            )
        elif usable and present / usable < 0.5:
            self.report.add(
                "warning",
                loc,
                kind,
                slug,
                "keyword_coverage_low",
                f"only {present}/{usable} keywords appear in the copy",
            )

    def _check_primary_keyword_metadata(
        self, loc: str, kind: str, slug: str, over: dict[str, Any], identity: Any
    ) -> None:
        keywords = over.get("keywords") or []
        if not isinstance(keywords, list) or not keywords:
            return
        primary = str(keywords[0]).strip().lower()
        metadata = " ".join(str(over.get(field) or "") for field in ("meta_title", "description")).lower()
        identity_text = str(identity or "").lower()
        if primary and primary not in metadata and primary not in identity_text:
            self.report.add(
                "warning",
                loc,
                kind,
                slug,
                "primary_keyword_not_in_metadata",
                f"primary keyword {primary!r} missing from title/description",
            )

    def _check_faqs(
        self, loc: str, kind: str, slug: str, faqs: list[Any], thresholds: Thresholds
    ) -> None:
        questions: set[str] = set()
        for index, faq in enumerate(faqs, start=1):
            if not isinstance(faq, dict):
                self.report.add("error", loc, kind, slug, "invalid_faq", f"FAQ #{index} is not an object")
                continue
            question = str(faq.get("q") or faq.get("question") or "").strip()
            answer = str(faq.get("a") or faq.get("answer") or "").strip()
            if not question or not answer:
                self.report.add("error", loc, kind, slug, "incomplete_faq", f"FAQ #{index} missing question/answer")
                continue
            normalized = question.lower()
            if normalized in questions:
                self.report.add("error", loc, kind, slug, "duplicate_faq", f"duplicate FAQ question: {question[:60]}")
            questions.add(normalized)
            answer_words = word_count(answer)
            if answer_words < thresholds.faq_answer_error:
                self.report.add(
                    "error",
                    loc,
                    kind,
                    slug,
                    "faq_answer_too_short",
                    f"FAQ #{index} answer has {answer_words} words (min {thresholds.faq_answer_error})",
                )
            elif answer_words < thresholds.faq_answer_warn:
                self.report.add(
                    "warning",
                    loc,
                    kind,
                    slug,
                    "faq_answer_short",
                    f"FAQ #{index} answer has {answer_words} words (target {thresholds.faq_answer_warn}+)",
                )

    def _remember_body(self, loc: str, kind: str, slug: str, body: Any) -> None:
        normalized = normalize_text(body)
        if len(normalized.split()) >= 50:
            self._bodies[(loc, kind, slug)] = normalized

    def _check_duplicates(self) -> None:
        # Duplicates are already reported while registering metadata. This hook
        # keeps the run order explicit for future keyword/slug checks.
        return None

    def _check_sitemaps(self) -> None:
        from app.core.config import settings
        from app.services.blog_service import BlogService
        from app.services.sitemap_service import SitemapService

        service = SitemapService(settings)
        base = settings.SITE_URL.rstrip("/")
        robots = service.build_robots_txt()
        if f"{base}/sitemap.xml" not in robots:
            self.report.add("error", "en", "sitemap", "-", "robots_missing_sitemap", "robots.txt missing /sitemap.xml")
        if "sitemap-index.xml" in robots:
            self.report.add("error", "en", "sitemap", "-", "legacy_sitemap_index_in_robots", "robots.txt still advertises sitemap-index.xml")

        xml = service.build_sitemap_xml()
        if "xhtml:link" in xml or "hreflang=" in xml:
            self.report.add("error", "en", "sitemap", "-", "legacy_hreflang_in_sitemap", "sitemap.xml contains hreflang alternates")
        listed: set[str] = set()
        for loc_url, _alts in self._xml_rows(xml):
            path = urllib.parse.urlparse(loc_url).path or "/"
            seg = path.strip("/").split("/", 1)[0].lower()
            if seg in LEGACY_LOCALE_PREFIXES:
                self.report.add("error", "en", "sitemap", path, "legacy_locale_url_in_sitemap", "sitemap.xml contains legacy locale path")
            listed.add(path)

        required_surfaces = ["/", "/tools", "/student-tools", "/blog"]
        required_surfaces += [f"/blog/{p}" for p in BlogService(settings).get_pillars()]
        required_surfaces += [f"/{h}" for h in settings.HUB_CATEGORIES if h != "pdf-tools"]
        for path in required_surfaces:
            if path not in listed:
                self.report.add("error", "en", "sitemap", path, "surface_missing_from_sitemap", "surface missing from sitemap.xml")

        for slug, raw in self.tools.items():
            if not raw.get("noindex") and f"/tool/{slug}" not in listed:
                self.report.add("error", "en", "tool", slug, "tool_missing_from_sitemap", "tool missing from sitemap.xml")
        for slug, raw in self.posts.items():
            pillar = str(raw.get("pillar") or "")
            bare = f"/blog/{pillar}/{slug}"
            if pillar and not raw.get("noindex") and bare not in listed:
                self.report.add("error", "en", "blog", slug, "post_missing_from_sitemap", "post missing from sitemap.xml")

    @staticmethod
    def _xml_rows(xml: str) -> list[tuple[str, list[tuple[str, str]]]]:
        try:
            root = ET.fromstring(xml)
        except ET.ParseError:
            return []
        ns = {
            "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
            "xhtml": "http://www.w3.org/1999/xhtml",
        }
        rows: list[tuple[str, list[tuple[str, str]]]] = []
        for url_el in root.findall("sm:url", ns):
            loc_el = url_el.find("sm:loc", ns)
            loc = (loc_el.text or "").strip() if loc_el is not None else ""
            alternates = [
                (link.get("hreflang") or "", link.get("href") or "")
                for link in url_el.findall("xhtml:link", ns)
            ]
            rows.append((loc, alternates))
        return rows

    @classmethod
    def _xml_locs(cls, xml: str) -> set[str]:
        return {loc for loc, _alternates in cls._xml_rows(xml) if loc}

    @classmethod
    def _xml_urls(cls, xml: str) -> list[str]:
        return [loc for loc, _alternates in cls._xml_rows(xml) if loc]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="English SEO and sitemap quality gate.")
    parser.add_argument("--slug", action="append", dest="slugs", default=[], help="only audit these tool/blog slugs")
    parser.add_argument("--no-sitemap", action="store_true", help="skip sitemap consistency checks")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    parser.add_argument("--max-issues", type=int, default=80, help="max human-readable issues to print (default 80)")
    parser.add_argument("--quiet", action="store_true", help="print the summary only")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    gate = QualityGate(
        locales=["en"],
        slugs=set(args.slugs) if args.slugs else None,
        check_sitemaps=not args.no_sitemap,
    )
    report = gate.run()

    if args.json:
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Quality gate: {report.items_checked} item(s), locales={','.join(report.locales)}")
        if not args.quiet:
            for shown, issue in enumerate(report.issues):
                if shown >= args.max_issues:
                    remaining = len(report.issues) - shown
                    print(f"... {remaining} more issue(s) omitted (use --max-issues)")
                    break
                print(f"{issue.severity.upper():7} {issue.locale:2} {issue.kind:4} {issue.slug} [{issue.code}] {issue.message}")
        errors_by_code = Counter(issue.code for issue in report.errors)
        warnings_by_code = Counter(issue.code for issue in report.warnings)
        print(f"Errors: {len(report.errors)} {dict(errors_by_code)}")
        print(f"Warnings: {len(report.warnings)} {dict(warnings_by_code)}")
        print("PASS" if report.passed else "FAIL")

    failed = bool(report.errors) or (args.strict and bool(report.warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
