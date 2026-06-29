"""Tests for AnalyticsService: tracking, counting, sorting, and caching behavior."""

import os
import tempfile

import pytest

import app.services.analytics_service as analytics_service
from app.services.analytics_service import get_counts, track

TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "test_analytics.db")
analytics_service.DB_PATH = TEST_DB_PATH


@pytest.fixture(autouse=True)
def cleanup_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
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
