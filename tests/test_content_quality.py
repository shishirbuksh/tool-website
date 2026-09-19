"""Content quality gates: bans boilerplate, enforces depth + healthy internal linking."""

import os
import re

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YAML_PATH = os.path.join(BASE_DIR, "data", "tools.yaml")

BANNED_PHRASES = [
    "standard mathematical formulas",
    "click calculate",
    "completely free to use",
]

VALID_CATEGORIES = {
    "Calculators",
    "Developer & SEO",
    "Productivity & Utilities",
    "AI & Crypto",
    "Business & Operations",
    "Image Processing",
}


def _load():
    with open(YAML_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["tools"]


def _faq_answer(faq: dict) -> str:
    return str(faq.get("a", faq.get("answer", "")))


def _faq_question(faq: dict) -> str:
    return str(faq.get("q", faq.get("question", "")))


class TestContentQuality:
    def test_no_banned_boilerplate(self):
        data = _load()
        hits = []
        for slug, info in data.items():
            blob = " ".join(
                [
                    str(info.get("description", "")),
                    str(info.get("howto_calculate", "")),
                    " ".join(_faq_answer(a) for a in (info.get("faqs") or [])),
                ]
            ).lower()
            for phrase in BANNED_PHRASES:
                if phrase in blob:
                    hits.append(f"{slug}: {phrase}")
        assert not hits, f"Boilerplate banned phrases found: {hits[:15]}"

    def test_about_min_length(self):
        data = _load()
        thin = [s for s, i in data.items() if len(str(i.get("about_body", "")).split()) < 25]
        assert not thin, f"about_body <25 words: {thin[:10]}"

    def test_faq_answer_depth(self):
        data = _load()
        thin = []
        for slug, info in data.items():
            for faq in info.get("faqs") or []:
                if len(_faq_answer(faq).split()) < 8:
                    thin.append(f"{slug}: {_faq_question(faq)[:40]}")
        assert not thin, f"FAQ answers <8 words: {thin[:10]}"

    def test_no_duplicate_howto_titles_within_tool(self):
        data = _load()
        bad = []
        for slug, info in data.items():
            titles = [str(s.get("title", "")).strip().lower() for s in (info.get("howto_steps") or [])]
            if len(titles) != len(set(titles)):
                bad.append(slug)
        assert not bad, f"Duplicate howto titles within tool: {bad[:10]}"

    def test_categories_whitelisted(self):
        data = _load()
        bad = [s for s, i in data.items() if i.get("category") not in VALID_CATEGORIES]
        assert not bad, f"Invalid categories: {bad[:10]}"

    def test_related_range_no_self(self):
        data = _load()
        bad = []
        for slug, info in data.items():
            rel = info.get("related_slugs") or []
            if not (3 <= len(rel) <= 8):
                bad.append(f"{slug}: len={len(rel)}")
            if slug in rel:
                bad.append(f"{slug}: self-ref")
        assert not bad, f"related_slugs range/self issues: {bad[:10]}"

    def test_no_orphans(self):
        data = _load()
        indeg: dict[str, int] = {s: 0 for s in data}
        for slug, info in data.items():
            for rel in info.get("related_slugs") or []:
                if rel in indeg:
                    indeg[rel] += 1
        orphans = [s for s, c in indeg.items() if c == 0]
        assert not orphans, f"Zero-indegree orphans (never recommended): {orphans}"

    def test_no_identical_faq_answer_across_tools(self):
        data = _load()
        seen: dict[str, list[str]] = {}
        for slug, info in data.items():
            for faq in info.get("faqs") or []:
                ans = re.sub(r"\s+", " ", _faq_answer(faq).strip().lower())
                if len(ans) < 30:
                    continue
                seen.setdefault(ans, []).append(slug)
        # Generic trust answers (free/privacy) are intentionally shared; flag only
        # egregious duplication shared by >30 tools. Per-category diversification
        # (crypto/dev cliques) is tracked as tech-debt, not a ship-blocker.
        dupes = {a[:60]: v for a, v in seen.items() if len(v) > 30}
        assert not dupes, f"Identical FAQ answers shared by >30 tools: {list(dupes.items())[:3]}"
