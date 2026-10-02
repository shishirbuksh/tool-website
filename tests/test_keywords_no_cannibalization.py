"""Keyword cannibalization guards: unique primaries, caps, no tool-blog collisions.

Locks in the 2026-10 multi-agent keyword panel outcome:
- tools avg ~7 keywords, zero exact duplicates tool-vs-tool or tool-vs-blog.
"""

import os
import re

import yaml

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_PATH = os.path.join(BASE_DIR, "data", "tools.yaml")
BLOG_PATH = os.path.join(BASE_DIR, "data", "blog.yaml")

# Tools with entity-distinct 10-keyword sets (exempt from the cap of 8).
CAP10_ALLOWLIST = {"regex-tester", "word-counter"}
TOOL_CAP = 8

# Category names must never appear inside keywords (stuffing, not user queries).
STUFFING_MARKERS = (
    "developer & seo",
    "ai & crypto crypto",
    "calculators break",
    "productivity & utilities pdf",
)


def _norm(s: str) -> str:
    s = str(s).lower().strip()
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s)


def _tools() -> dict:
    with open(TOOLS_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["tools"]


def _posts() -> dict:
    with open(BLOG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["posts"]


class TestToolKeywords:
    def test_tool_keyword_cap(self) -> None:
        bad = {
            s: len(v.get("keywords") or [])
            for s, v in _tools().items()
            if len(v.get("keywords") or []) > (10 if s in CAP10_ALLOWLIST else TOOL_CAP)
        }
        assert not bad, f"tool keyword cap breached: {bad}"

    def test_tool_keywords_unique_within_page(self) -> None:
        bad = []
        for s, v in _tools().items():
            kws = [str(k).lower().strip() for k in (v.get("keywords") or [])]
            if len(kws) != len(set(kws)):
                bad.append(s)
        assert not bad, f"dupe keywords within tool: {bad}"

    def test_no_exact_duplicate_across_tools(self) -> None:
        seen: dict[str, str] = {}
        dupes = []
        for slug, info in _tools().items():
            for kw in info.get("keywords") or []:
                key = str(kw).lower().strip()
                if key in seen and seen[key] != slug:
                    dupes.append(f"{kw!r}: {seen[key]} + {slug}")
                seen.setdefault(key, slug)
        assert not dupes, f"exact keyword shared by 2 tools: {dupes[:10]}"

    def test_no_category_stuffing(self) -> None:
        bad = [
            f"{slug}: {kw}"
            for slug, info in _tools().items()
            for kw in (info.get("keywords") or [])
            if any(m in str(kw).lower() for m in STUFFING_MARKERS)
        ]
        assert not bad, f"category-stuffed keywords: {bad[:10]}"

    def test_no_todo_placeholders(self) -> None:
        bad = [
            slug
            for slug, info in _tools().items()
            if "TODO" in str(info.get("howto_calculate", ""))
        ]
        assert not bad, f"howto_calculate TODO placeholders: {bad[:10]}"

    def test_meta_title_length(self) -> None:
        bad = {
            s: len(str(v.get("meta_title", "")))
            for s, v in _tools().items()
            if v.get("meta_title") and len(str(v.get("meta_title"))) > 60
        }
        assert not bad, f"meta_title >60 chars (SERP truncate): {bad}"

    def test_tool_faq_cap(self) -> None:
        bad = {
            s: len(v.get("faqs") or [])
            for s, v in _tools().items()
            if len(v.get("faqs") or []) > 10
        }
        assert not bad, f"tool FAQ cap breached: {bad}"


class TestToolBlogDecoupling:
    def test_no_exact_tool_blog_keyword_overlap(self) -> None:
        tool_norms: dict[str, str] = {}
        for slug, info in _tools().items():
            for kw in info.get("keywords") or []:
                tool_norms.setdefault(_norm(kw), f"tool:{slug}")
        collisions = []
        for slug, info in _posts().items():
            for kw in info.get("keywords") or []:
                if _norm(kw) in tool_norms:
                    collisions.append(f"{kw!r}: {tool_norms[_norm(kw)]} + blog:{slug}")
        assert not collisions, f"tool-blog keyword collisions: {collisions[:10]}"
