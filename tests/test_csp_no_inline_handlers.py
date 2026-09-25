"""CSP hygiene: nonce-based script-src and no inline event-handler attributes."""

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
MIDDLEWARE_PATH = os.path.join(BASE_DIR, "app", "core", "middleware.py")

# HTML-attribute handlers blocked by nonce CSP (leading whitespace required so
# JS property assignments like ``el.onclick = fn`` do not match).
GLOBAL_BANNED_RE = re.compile(r'\s(onclick|onsubmit|onload)\s*=\s*["\']', re.IGNORECASE)
BASE_BANNED_RE = re.compile(
    r"\s(onclick|onsubmit|onload|onchange|oninput|onerror|onfocus|onblur|onkeydown|onkeyup)\s*=\s*[\"']",
    re.IGNORECASE,
)

BASE_TEMPLATES = [
    os.path.join(TEMPLATES_DIR, "base.html"),
    os.path.join(TEMPLATES_DIR, "tool_base.html"),
    os.path.join(TEMPLATES_DIR, "hub.html"),
    os.path.join(TEMPLATES_DIR, "index.html"),
    os.path.join(TEMPLATES_DIR, "components", "tool_layout.html"),
]


def _iter_template_files() -> list[str]:
    found: list[str] = []
    for root, _, files in os.walk(TEMPLATES_DIR):
        for name in files:
            if name.endswith(".html"):
                found.append(os.path.join(root, name))
    return sorted(found)


class TestCspNoInlineHandlers:
    def test_script_src_uses_nonce(self) -> None:
        with open(MIDDLEWARE_PATH, encoding="utf-8") as f:
            src = f.read()
        assert "script-src 'nonce-" in src, "SecurityHeadersMiddleware must build nonce-based script-src"
        idx = src.find("script-src")
        snippet = src[max(0, idx - 200) : idx + 500]
        assert "unsafe-inline" not in snippet, "script-src must not allow 'unsafe-inline'"

    def test_base_template_uses_nonce(self) -> None:
        with open(os.path.join(TEMPLATES_DIR, "base.html"), encoding="utf-8") as f:
            base = f.read()
        assert 'nonce="{{ nonce }}"' in base, "base.html scripts must carry nonce={{ nonce }}"

    def test_no_banned_handlers_anywhere(self) -> None:
        hits: list[str] = []
        for path in _iter_template_files():
            with open(path, encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    if GLOBAL_BANNED_RE.search(line):
                        hits.append(f"{os.path.relpath(path, BASE_DIR)}:{lineno}")
        assert not hits, f"Inline handlers blocked by CSP found: {hits[:10]}"

    def test_no_handlers_in_base_templates(self) -> None:
        hits: list[str] = []
        for path in BASE_TEMPLATES:
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8", errors="ignore") as f:
                for lineno, line in enumerate(f, 1):
                    if BASE_BANNED_RE.search(line):
                        hits.append(f"{os.path.relpath(path, BASE_DIR)}:{lineno}")
        assert not hits, f"Inline handlers in base templates: {hits[:10]}"
