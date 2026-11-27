"""Tests for YouTubeService channel normalization, parsing, and caching."""

from django.core.cache import cache

from apps.tools_api.services.youtube_service import (
    YouTubeService,
    detect_niche,
    normalize_youtube_handle,
    parse_channel_html,
    parse_compact_count,
)


def test_normalize_youtube_handle():
    assert normalize_youtube_handle("https://www.youtube.com/@mkbhd") == "mkbhd"
    assert normalize_youtube_handle("@Veritasium") == "Veritasium"
    assert normalize_youtube_handle("Mr Beast") == "MrBeast"
    assert normalize_youtube_handle("   ") == ""


def test_parse_compact_count_and_niche():
    assert parse_compact_count("1.5M") == 1_500_000
    assert parse_compact_count("42K") == 42_000
    assert parse_compact_count("2B") == 2_000_000_000
    assert parse_compact_count("bad") == 0
    assert detect_niche("AI coding & software review")[0] == "tech"
    assert detect_niche("Crypto & stock wealth")[0] == "finance"


def test_parse_channel_html_extracts_stats():
    sample_html = (
        '<meta property="og:title" content="Tech &amp; AI Lab">'
        '<meta property="og:description" content="Weekly coding &amp; AI software guides">'
        '<meta property="og:image" content="https://yt3.googleusercontent.com/avatar.jpg">'
        "<span>2.5M subscribers</span><span>410 videos</span>"
    )
    parsed = parse_channel_html("techailab", sample_html)
    assert parsed["success"] is True
    assert parsed["title"] == "Tech & AI Lab"
    assert parsed["subs_num"] == 2_500_000
    assert parsed["vids_num"] == 410
    assert parsed["niche"] == "tech"
    assert parsed["avatar"] == "https://yt3.googleusercontent.com/avatar.jpg"


def test_youtube_service_caches_success(monkeypatch):
    cache.delete("yt_ch_testchan")
    monkeypatch.setattr(
        "apps.tools_api.services.youtube_service._fetch_channel_html",
        lambda h: '<meta property="og:title" content="Test Channel"><span>10K subscribers</span>',
    )
    svc = YouTubeService()
    payload, status = svc.fetch_channel_stats("@testchan")
    assert status == 200
    assert payload["subs_num"] == 10_000
    payload2, status2 = svc.fetch_channel_stats("testchan")
    assert status2 == 200
    assert payload2["title"] == "Test Channel"
