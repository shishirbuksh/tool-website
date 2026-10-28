#!/usr/bin/env python3
"""Apply one localized content pack to ``data/tools.yaml`` / ``data/blog.yaml``.

A pack is a small YAML file that contains only the override that should change::

    locale: de
    wave: 1a
    tools:
      emi-calculator:
        name: Kreditrechner
        ...
    posts:
      compound-interest-formula:
        title: ...
        ...

The applier never re-serializes a whole content file. It locates the exact
``i18n.<locale>`` block, replaces those lines, and then reloads both the old and
new YAML to prove that every other item, locale and top-level field is
semantically unchanged. Line endings (the repository uses CRLF in both content
files) are preserved.

Usage:
  python scripts/apply_content_pack.py data/content_packs/de_wave1a.yaml
  python scripts/apply_content_pack.py data/content_packs/de_wave1a.yaml --write
  python scripts/apply_content_pack.py data/content_packs/de_wave1a.yaml --write --allow-published

Without ``--write`` the command is a dry run and prints a summary only.
Exit codes: 0 = success, 2 = invalid pack or unsafe merge.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, NoReturn

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTENT_FILES = {
    "tool": REPO_ROOT / "data" / "tools.yaml",
    "blog": REPO_ROOT / "data" / "blog.yaml",
}
SECTION_KEYS = {"tool": "tools", "blog": "posts"}
VALID_LOCALES = frozenset({"de", "es", "fr", "hi"})
VALID_STATUSES = frozenset({"draft", "review", "published"})

COMMON_FIELDS = frozenset(
    {
        "meta_title",
        "description",
        "keywords",
        "faqs",
        "howto_steps",
        "date_modified",
        "translation_status",
        "reviewer",
        "reviewed_at",
        "author",
        "sources",
        "noindex",
    }
)
TOOL_FIELDS = COMMON_FIELDS | {"name", "howto_calculate", "about_title", "about_body"}
BLOG_FIELDS = COMMON_FIELDS | {"title", "body_html"}
ALLOWED_FIELDS = {"tool": TOOL_FIELDS, "blog": BLOG_FIELDS}
REQUIRED_FIELDS = {
    "tool": frozenset(
        {
            "name",
            "meta_title",
            "description",
            "keywords",
            "faqs",
            "howto_steps",
            "howto_calculate",
            "about_title",
            "about_body",
            "translation_status",
            "author",
            "sources",
        }
    ),
    "blog": frozenset(
        {
            "title",
            "meta_title",
            "description",
            "keywords",
            "faqs",
            "howto_steps",
            "body_html",
            "translation_status",
            "author",
            "sources",
        }
    ),
}

_ARTIFACT_PATTERNS = (
    ("replacement_char", re.compile("\ufffd")),
    ("lsi_scaffold", re.compile(r"\bLSI\s*:", re.IGNORECASE)),
    ("todo_marker", re.compile(r"\b(?:TODO|FIXME|TBD)\s*:", re.IGNORECASE)),
    ("lorem_ipsum", re.compile(r"lorem ipsum", re.IGNORECASE)),
    ("template_placeholder", re.compile(r"\{\{|\}\}|\[insert|\[translate", re.IGNORECASE)),
)
_TAG_RE = re.compile(r"<[^>]+>")
_H2_RE = re.compile(r"<h2\b", re.IGNORECASE)
_LINK_RE = re.compile(r"<a\b[^>]*\bhref=[\"'](?:/|https?://(?:www\.)?storybrainai\.com)", re.IGNORECASE)
_YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class PackError(ValueError):
    """A pack is invalid or the merge would change something outside its target."""


def _fail(message: str) -> NoReturn:
    raise PackError(message)


@dataclass(frozen=True)
class Pack:
    locale: str
    tools: dict[str, dict[str, Any]]
    posts: dict[str, dict[str, Any]]
    wave: str = ""
    source: Path | None = None


@dataclass(frozen=True)
class Change:
    kind: str
    slug: str
    path: Path
    replaced: bool


def html_to_text(value: Any) -> str:
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", str(value or ""))).strip()


def word_count(value: Any) -> int:
    return len(html_to_text(value).split())


def _require_string(value: Any, field: str, slug: str) -> str:
    if not isinstance(value, str) or not value.strip():
        _fail(f"{slug}: {field} must be a non-empty string")
    return value.strip()


def _require_string_list(value: Any, field: str, slug: str, *, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum:
        _fail(f"{slug}: {field} must be a list with at least {minimum} item(s)")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            _fail(f"{slug}: {field} contains an empty/non-string item")
        result.append(item.strip())
    return result


def _validate_faqs(value: Any, slug: str, *, minimum: int = 5) -> None:
    if not isinstance(value, list) or len(value) < minimum:
        _fail(f"{slug}: faqs must contain at least {minimum} entries")
    seen: set[str] = set()
    for index, faq in enumerate(value, start=1):
        if not isinstance(faq, dict):
            _fail(f"{slug}: FAQ #{index} must be an object")
        question = _require_string(faq.get("q"), f"faqs[{index}].q", slug)
        _require_string(faq.get("a"), f"faqs[{index}].a", slug)
        key = question.casefold()
        if key in seen:
            _fail(f"{slug}: duplicate FAQ question {question!r}")
        seen.add(key)


def _validate_howto(value: Any, slug: str) -> None:
    if not isinstance(value, list) or not value:
        _fail(f"{slug}: howto_steps must be a non-empty list")
    for index, step in enumerate(value, start=1):
        if not isinstance(step, dict):
            _fail(f"{slug}: howto_steps[{index}] must be an object")
        _require_string(step.get("title"), f"howto_steps[{index}].title", slug)
        _require_string(step.get("desc"), f"howto_steps[{index}].desc", slug)


def _validate_sources(value: Any, slug: str) -> None:
    sources = _require_string_list(value, "sources", slug)
    for source in sources:
        parsed = urllib.parse.urlparse(source)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            _fail(f"{slug}: source is not an http(s) URL: {source!r}")


def _iter_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)


def _validate_override(kind: str, slug: str, override: Any) -> None:
    if not isinstance(override, dict) or not override:
        _fail(f"{slug}: override must be a non-empty object")
    unknown = set(override) - ALLOWED_FIELDS[kind]
    if unknown:
        _fail(f"{slug}: unsupported field(s): {', '.join(sorted(unknown))}")
    missing = REQUIRED_FIELDS[kind] - set(override)
    if missing:
        _fail(f"{slug}: missing required field(s): {', '.join(sorted(missing))}")

    if kind == "tool":
        _require_string(override.get("name"), "name", slug)
        _require_string(override.get("about_title"), "about_title", slug)
        _require_string(override.get("about_body"), "about_body", slug)
        _require_string(override.get("howto_calculate"), "howto_calculate", slug)
    else:
        _require_string(override.get("title"), "title", slug)
        _require_string(override.get("body_html"), "body_html", slug)

    _require_string(override.get("meta_title"), "meta_title", slug)
    _require_string(override.get("description"), "description", slug)
    _require_string_list(override.get("keywords"), "keywords", slug, minimum=4)
    _validate_faqs(override.get("faqs"), slug)
    _validate_howto(override.get("howto_steps"), slug)
    _validate_sources(override.get("sources"), slug)

    status = _require_string(override.get("translation_status"), "translation_status", slug).lower()
    if status not in VALID_STATUSES:
        _fail(f"{slug}: translation_status must be one of {sorted(VALID_STATUSES)}")
    if status == "published" and override.get("noindex") is True:
        _fail(f"{slug}: published override cannot also set noindex: true")

    reviewer = str(override.get("reviewer") or "").strip()
    reviewed_at = str(override.get("reviewed_at") or "").strip()
    if bool(reviewer) != bool(reviewed_at):
        _fail(f"{slug}: reviewer and reviewed_at must be supplied together")
    if reviewed_at:
        try:
            date.fromisoformat(reviewed_at)
        except ValueError as exc:
            message = f"{slug}: reviewed_at must be YYYY-MM-DD"
            raise PackError(message) from exc

    modified = override.get("date_modified")
    if modified is not None:
        try:
            date.fromisoformat(str(modified))
        except ValueError as exc:
            message = f"{slug}: date_modified must be YYYY-MM-DD"
            raise PackError(message) from exc

    for field, value in override.items():
        for text in _iter_strings(value):
            for code, pattern in _ARTIFACT_PATTERNS:
                if pattern.search(text):
                    _fail(f"{slug}: {field} contains localization artifact {code}")


def load_pack(path: Path) -> Pack:
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_YAML_LOADER) or {}
    except FileNotFoundError as exc:
        message = f"pack not found: {path}"
        raise PackError(message) from exc
    except yaml.YAMLError as exc:
        message = f"pack is not valid YAML: {exc}"
        raise PackError(message) from exc
    if not isinstance(raw, dict):
        raise PackError("pack root must be an object")
    unknown = set(raw) - {"locale", "wave", "tools", "posts"}
    if unknown:
        _fail(f"unsupported pack field(s): {', '.join(sorted(unknown))}")

    locale = str(raw.get("locale") or "").strip().lower()
    if locale not in VALID_LOCALES:
        _fail(f"locale must be one of {sorted(VALID_LOCALES)}")
    tools = raw.get("tools") or {}
    posts = raw.get("posts") or {}
    if not isinstance(tools, dict) or not isinstance(posts, dict):
        raise PackError("tools/posts must be objects")
    if not tools and not posts:
        raise PackError("pack contains no tools or posts")

    for slug, override in tools.items():
        if not isinstance(slug, str) or not slug.strip():
            raise PackError("tool slug must be a non-empty string")
        _validate_override("tool", slug, override)
    for slug, override in posts.items():
        if not isinstance(slug, str) or not slug.strip():
            raise PackError("post slug must be a non-empty string")
        _validate_override("blog", slug, override)

    return Pack(
        locale=locale,
        tools={str(slug): override for slug, override in tools.items()},
        posts={str(slug): override for slug, override in posts.items()},
        wave=str(raw.get("wave") or ""),
        source=path,
    )


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _line_text(line: str) -> str:
    return line.rstrip("\n")


def _find_section(lines: list[str], section: str) -> tuple[int, int]:
    marker = f"{section}:"
    start = next((index for index, line in enumerate(lines) if _line_text(line) == marker), -1)
    if start < 0:
        _fail(f"top-level {section!r} section not found")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = _line_text(lines[index])
        if line and not line.startswith(" ") and line != marker:
            end = index
            break
    return start, end


def _find_item(lines: list[str], section: str, slug: str) -> tuple[int, int]:
    section_start, section_end = _find_section(lines, section)
    marker = f"  {slug}:"
    start = next((index for index in range(section_start + 1, section_end) if _line_text(lines[index]) == marker), -1)
    if start < 0:
        _fail(f"{section}.{slug} not found")
    end = section_end
    for index in range(start + 1, section_end):
        line = _line_text(lines[index])
        if line and _line_indent(line) <= 2:
            end = index
            break
    return start, end


def _find_i18n(lines: list[str], item_start: int, item_end: int) -> tuple[int, int] | None:
    start = next(
        (index for index in range(item_start + 1, item_end) if _line_text(lines[index]) == "    i18n:"),
        -1,
    )
    if start < 0:
        return None
    end = item_end
    for index in range(start + 1, item_end):
        line = _line_text(lines[index])
        if line and _line_indent(line) <= 4:
            end = index
            break
    return start, end


def _find_locale(lines: list[str], i18n_start: int, i18n_end: int, locale: str) -> tuple[int, int] | None:
    marker = f"      {locale}:"
    start = next(
        (index for index in range(i18n_start + 1, i18n_end) if _line_text(lines[index]) == marker),
        -1,
    )
    if start < 0:
        return None
    end = i18n_end
    for index in range(start + 1, i18n_end):
        line = _line_text(lines[index])
        if line and _line_indent(line) <= 6:
            end = index
            break
    while end > start + 1 and not _line_text(lines[end - 1]).strip():
        end -= 1
    return start, end


def _serialize_override(override: dict[str, Any]) -> list[str]:
    dumped = yaml.safe_dump(
        override,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=100,
    )
    return ["        " + line + "\n" for line in dumped.splitlines()]


def replace_override(text: str, *, kind: str, slug: str, locale: str, override: dict[str, Any]) -> str:
    """Replace one ``i18n.<locale>`` block in normalized-LF YAML text."""
    if kind not in SECTION_KEYS:
        _fail(f"unknown content kind: {kind!r}")
    if locale not in VALID_LOCALES:
        _fail(f"unknown locale: {locale!r}")
    _validate_override(kind, slug, override)

    lines = text.splitlines(keepends=True)
    section = SECTION_KEYS[kind]
    item_start, item_end = _find_item(lines, section, slug)
    i18n_block = _find_i18n(lines, item_start, item_end)
    replacement = [f"      {locale}:\n", *_serialize_override(override)]

    if i18n_block is None:
        insert_at = item_end
        while insert_at > item_start + 1 and not _line_text(lines[insert_at - 1]).strip():
            insert_at -= 1
        new_block = ["    i18n:\n", *replacement]
        if insert_at > 0 and not lines[insert_at - 1].endswith("\n"):
            lines[insert_at - 1] += "\n"
        lines[insert_at:insert_at] = new_block
        return "".join(lines)

    i18n_start, i18n_end = i18n_block
    locale_block = _find_locale(lines, i18n_start, i18n_end, locale)
    if locale_block is None:
        insert_at = i18n_end
        while insert_at > i18n_start + 1 and not _line_text(lines[insert_at - 1]).strip():
            insert_at -= 1
        if insert_at > 0 and not lines[insert_at - 1].endswith("\n"):
            lines[insert_at - 1] += "\n"
        lines[insert_at:insert_at] = replacement
        return "".join(lines)

    start, end = locale_block
    lines[start:end] = replacement
    return "".join(lines)


def _verify_merge(
    old_root: dict[str, Any],
    new_root: dict[str, Any],
    *,
    kind: str,
    slug: str,
    locale: str,
    override: dict[str, Any],
) -> None:
    section = SECTION_KEYS[kind]
    old_section = old_root.get(section)
    new_section = new_root.get(section)
    if not isinstance(old_section, dict) or not isinstance(new_section, dict):
        _fail(f"{section} section is not an object after merge")
    if set(old_section) != set(new_section):
        _fail(f"{section} key set changed; refusing to write")

    for key, value in old_section.items():
        if key != slug and new_section.get(key) != value:
            _fail(f"merge changed unrelated item {section}.{key}")

    old_item = old_section.get(slug)
    new_item = new_section.get(slug)
    if not isinstance(old_item, dict) or not isinstance(new_item, dict):
        _fail(f"{section}.{slug} is not an object")

    old_plain = {key: value for key, value in old_item.items() if key != "i18n"}
    new_plain = {key: value for key, value in new_item.items() if key != "i18n"}
    if old_plain != new_plain:
        _fail(f"merge changed non-i18n fields of {section}.{slug}")

    old_i18n = old_item.get("i18n") or {}
    new_i18n = new_item.get("i18n") or {}
    if not isinstance(old_i18n, dict) or not isinstance(new_i18n, dict):
        _fail(f"{section}.{slug}.i18n is not an object")
    if set(old_i18n) - {locale} != set(new_i18n) - {locale}:
        _fail(f"merge changed locale key set of {section}.{slug}")
    for other_locale, value in old_i18n.items():
        if other_locale != locale and new_i18n.get(other_locale) != value:
            _fail(f"merge changed {section}.{slug}.i18n.{other_locale}")
    if new_i18n.get(locale) != override:
        _fail(f"merge did not produce the requested {section}.{slug}.i18n.{locale} block")


def _load_yaml(text: str) -> dict[str, Any]:
    try:
        loaded = yaml.load(text, Loader=_YAML_LOADER) or {}
    except yaml.YAMLError as exc:
        message = f"merged file is not valid YAML: {exc}"
        raise PackError(message) from exc
    if not isinstance(loaded, dict):
        raise PackError("merged file root is not an object")
    return loaded


def apply_pack(pack: Pack, *, write: bool = False, allow_published: bool = False) -> list[Change]:
    changes: list[Change] = []
    for kind, items in (("tool", pack.tools), ("blog", pack.posts)):
        if not items:
            continue
        path = CONTENT_FILES[kind]
        raw_bytes = path.read_bytes()
        text = raw_bytes.decode("utf-8")
        newline = "\r\n" if "\r\n" in text else "\n"
        normalized = text.replace("\r\n", "\n")
        for slug, override in items.items():
            status = str(override.get("translation_status") or "").strip().lower()
            if status == "published" and not allow_published:
                _fail(f"{slug}: refusing to apply a published pack without --allow-published")
            old_root = _load_yaml(normalized)
            normalized = replace_override(normalized, kind=kind, slug=slug, locale=pack.locale, override=override)
            new_root = _load_yaml(normalized)
            _verify_merge(old_root, new_root, kind=kind, slug=slug, locale=pack.locale, override=override)
            changes.append(Change(kind, slug, path, True))
        if write:
            path.write_bytes(normalized.replace("\n", newline).encode("utf-8"))
    return changes


def _summary(pack: Pack) -> str:
    lines = [f"locale={pack.locale} wave={pack.wave or '-'} tools={len(pack.tools)} posts={len(pack.posts)}"]
    for kind, items in (("tool", pack.tools), ("blog", pack.posts)):
        for slug, override in items.items():
            body = override.get("about_body") if kind == "tool" else override.get("body_html")
            faqs = override.get("faqs") or []
            h2 = len(_H2_RE.findall(str(body or "")))
            links = len(_LINK_RE.findall(str(body or "")))
            lines.append(
                f"  {kind:4s} {slug}: words={word_count(body)} faqs={len(faqs)} h2={h2} links={links} "
                f"status={override.get('translation_status')}"
            )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply one localized content pack without rewriting the whole YAML file.")
    parser.add_argument("pack", type=Path, help="pack YAML file")
    parser.add_argument("--write", action="store_true", help="write the merge (default: dry run)")
    parser.add_argument(
        "--allow-published",
        action="store_true",
        help="allow translation_status=published (release still requires the locale gate)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        pack = load_pack(args.pack)
        print(_summary(pack))
        changes = apply_pack(pack, write=args.write, allow_published=args.allow_published)
    except PackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for change in changes:
        print(f"{'wrote' if args.write else 'would write'} {change.path} [{change.kind}:{change.slug}]")
    if not args.write:
        print("dry run: pass --write to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
