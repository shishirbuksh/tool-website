"""YouTube public channel stats lookup service (no API key required)."""

from __future__ import annotations

import html as html_lib
import logging
import re
import urllib.request
from typing import Any

from django.core.cache import cache

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_AVATAR_HOSTS = ("googleusercontent.com", "ggpht.com", "ytimg.com")
_NICHE_RULES: list[tuple[tuple[str, ...], str, float, int]] = [
    (("sport", "league", "football", "cricket", "nba", "soccer", "match", "isl"), "sports", 4.0, 40),
    (("finance", "money", "invest", "stock", "crypto", "wealth"), "finance", 20.0, 20),
    (("tech", "code", "software", "ai", "gadget", "iphone", "hardware"), "tech", 12.0, 25),
    (("game", "gaming", "play", "minecraft", "roblox", "fortnite"), "gaming", 3.5, 35),
    (("science", "learn", "education", "study", "math", "physics"), "education", 10.0, 20),
    (("fit", "fitness", "gym", "workout"), "fitness", 8.0, 35),
    (("cook", "food", "recipe", "kitchen"), "food", 8.0, 30),
]


def normalize_youtube_handle(query: str) -> str:
    """Normalize a raw @handle, URL, or channel query into a safe handle token."""
    raw = (query or "").strip()
    if not raw:
        return ""
    m_url = re.search(r"youtube\.com/@([a-zA-Z0-9_\-\.]+)", raw)
    if m_url:
        handle = m_url.group(1)
    elif raw.startswith("@"):
        handle = raw[1:].strip()
    else:
        handle = raw.replace(" ", "").strip()
    return re.sub(r"[^a-zA-Z0-9_\-\.]", "", handle)


def parse_compact_count(raw_text: str | None) -> int:
    """Parse compact K/M/B count strings into integers."""
    if not raw_text:
        return 0
    text = raw_text.strip().upper()
    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    try:
        if text[-1:] in multipliers:
            return int(float(text[:-1]) * multipliers[text[-1]])
        return int(float(text))
    except (ValueError, TypeError):
        return 0


def detect_niche(text_corpus: str) -> tuple[str, float, int]:
    """Infer channel niche, baseline CPM, and Shorts mix ratio from channel text."""
    lower = text_corpus.lower()
    for keywords, niche, cpm, shorts_pct in _NICHE_RULES:
        if any(w in lower for w in keywords):
            return niche, cpm, shorts_pct
    return "entertainment", 3.5, 35


def _fetch_channel_html(handle: str) -> str:
    url = f"https://www.youtube.com/@{handle}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _USER_AGENT, "Accept-Language": "en-US,en;q=0.9"},
    )
    with urllib.request.urlopen(req, timeout=6) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_channel_html(handle: str, html: str) -> dict[str, Any]:
    """Extract channel title, subscriber/video counts, avatar, and niche from YouTube HTML."""
    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', html)
    title = html_lib.unescape(title_match.group(1)) if title_match else f"@{handle}"

    desc_match = re.search(r'<meta property="og:description" content="([^"]+)"', html)
    description = html_lib.unescape(desc_match.group(1)) if desc_match else ""

    sub_match = re.search(r"([0-9\.]+[KMkm]?)\s+subscribers", html)
    subs_text = sub_match.group(1).upper() if sub_match else None
    if not subs_text:
        sub_acc = re.search(
            r'"subscriberCountText":\{"accessibility":\{"accessibilityData":\{"label":"([^"]+)"',
            html,
        )
        if sub_acc:
            label = sub_acc.group(1)
            for pattern, suffix in (
                (r"([0-9\.]+)\s+billion", "B"),
                (r"([0-9\.]+)\s+million", "M"),
                (r"([0-9\.]+)\s+thousand", "K"),
            ):
                m = re.search(pattern, label, re.IGNORECASE)
                if m:
                    subs_text = f"{m.group(1)}{suffix}"
                    break

    subs_num = parse_compact_count(subs_text)

    vid_match = re.search(r"([0-9\.]+[KMkm]?)\s+videos", html)
    vids_text = vid_match.group(1).upper() if vid_match else None
    vids_num = parse_compact_count(vids_text)

    avatar_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    raw_avatar = avatar_match.group(1) if avatar_match else None
    avatar = (
        raw_avatar
        if raw_avatar and raw_avatar.startswith("https://") and any(d in raw_avatar for d in _AVATAR_HOSTS)
        else None
    )

    niche, cpm, shorts_pct = detect_niche(f"{title} {handle} {description}")
    estimated_views = max(25_000, int(subs_num * 1.25)) if subs_num > 0 else 100_000

    return {
        "success": True,
        "title": title,
        "handle": f"@{handle}",
        "subs_text": subs_text or "Growing",
        "subs_num": subs_num,
        "vids_text": vids_text or "Active",
        "vids_num": vids_num,
        "avatar": avatar,
        "niche": niche,
        "cpm": cpm,
        "shorts_pct": shorts_pct,
        "estimated_views": estimated_views,
    }


class YouTubeService:
    """Service wrapper for cached YouTube public channel lookups."""

    def __init__(self, settings: Any = None) -> None:
        self.settings = settings

    def fetch_channel_stats(self, query: str) -> tuple[dict[str, Any], int]:
        """Return (payload, status_code) for a YouTube channel query."""
        raw_query = (query or "").strip()
        if not raw_query:
            return {"success": False, "message": "Query parameter required"}, 400

        handle = normalize_youtube_handle(raw_query)
        if not handle:
            return {"success": False, "message": "Invalid YouTube handle format."}, 400

        cache_key = f"yt_ch_{handle.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return cached, 200

        try:
            html = _fetch_channel_html(handle)
            res_data = parse_channel_html(handle, html)
            cache.set(cache_key, res_data, 7200)
            return res_data, 200
        except Exception as e:
            logger.warning("YouTube real-time fetch failed for %s: %s", handle, e)
            neg_data = {"success": False, "error": "Failed to fetch channel statistics", "handle": f"@{handle}"}
            cache.set(cache_key, neg_data, 60)
            return neg_data, 200
