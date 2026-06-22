import os
import pytest
from app.services.analytics_service import track, get_counts, DB_PATH


@pytest.fixture(autouse=True)
def cleanup_db():
    yield
    try:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
    except OSError:
        pass


class TestAnalyticsService:
    def test_track_and_get_counts(self):
        track("test_tool_1", "page_view")
        counts = get_counts(limit=10)
        assert isinstance(counts, dict)
        assert counts.get("test_tool_1", 0) >= 1

    def test_multiple_tracks(self):
        track("test_tool_2", "page_view")
        track("test_tool_2", "page_view")
        track("test_tool_2", "page_view")
        counts = get_counts(limit=10)
        assert counts.get("test_tool_2", 0) >= 3

    def test_get_counts_returns_sorted(self):
        track("test_popular", "page_view")
        track("test_popular", "page_view")
        track("test_popular", "page_view")
        track("test_popular", "page_view")
        counts = get_counts(limit=5)
        keys = list(counts.keys())
        if len(keys) > 1:
            assert counts[keys[0]] >= counts[keys[1]]

    def test_get_counts_empty(self):
        counts = get_counts(limit=0)
        assert isinstance(counts, dict)

    def test_track_empty_name(self):
        track("", "test")
        counts = get_counts(limit=10)
        assert "" in counts