import os

import pytest

from app.core.icons import LUCIDE_PATH, _cache, lucide_icon


class TestLucideIcon:
    def setup_method(self):
        _cache.clear()

    def test_missing_icon_returns_placeholder(self):
        result = lucide_icon("nonexistent-icon-name")
        assert 'icon-missing' in result
        assert 'not found' in result

    def test_icon_caches_result(self):
        if not os.path.isdir(LUCIDE_PATH):
            pytest.skip("lucide-static not installed")
        result1 = lucide_icon("home")
        result2 = lucide_icon("home")
        assert result1 == result2
        assert 'icon-missing' not in result1

    def test_icon_with_class_and_size(self):
        if not os.path.isdir(LUCIDE_PATH):
            pytest.skip("lucide-static not installed")
        result = lucide_icon("home", class_name="my-icon", size=32)
        assert 'class="my-icon"' in result
        assert 'width="32"' in result
        assert 'height="32"' in result
        assert 'aria-hidden="true"' in result

    def test_cache_hit_returns_same(self):
        if not os.path.isdir(LUCIDE_PATH):
            pytest.skip("lucide-static not installed")
        result1 = lucide_icon("home", class_name="x")
        result2 = lucide_icon("home", class_name="x")
        assert result1 == result2
