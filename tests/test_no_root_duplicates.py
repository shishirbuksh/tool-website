"""Root hygiene: one-off fix/remove/patch scripts must not live at repo root."""

import glob
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REMOVED_JUNK = [
    "remove_js.py",
    "remove_js2.py",
    "remove_build.py",
    "fix2.py",
    "fix_syntax.py",
    "patch_deploy.py",
]


class TestNoRootDuplicates:
    def test_junk_scripts_removed(self) -> None:
        leftover = [f for f in REMOVED_JUNK if os.path.exists(os.path.join(BASE_DIR, f))]
        assert not leftover, f"Stray root scripts still present: {leftover}"

    def test_no_stray_prefix_scripts(self) -> None:
        hits: list[str] = []
        for pattern in ("fix_*.py", "remove_*.py", "patch_*.py"):
            hits.extend(os.path.basename(p) for p in glob.glob(os.path.join(BASE_DIR, pattern)) if os.path.isfile(p))
        assert not hits, f"Stray prefixed scripts at root: {sorted(hits)}"
