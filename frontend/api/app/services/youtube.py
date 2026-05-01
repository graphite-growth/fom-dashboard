"""YouTube Data API v3 client — replaces Supermetrics YTPD connector."""

import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

YT_API_BASE = "https://www.googleapis.com/youtube/v3"
API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# ISO 8601 duration like "PT1H7M57S" / "PT38M59S" / "PT53S"
_DURATION_RE = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def _parse_duration_seconds(iso: str) -> int:
    """Convert ISO 8601 duration (e.g. PT38M59S) to total seconds."""
    if not iso:
        return 0
    m = _DURATION_RE.fullmatch(iso)
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

# Shared httpx client
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=30.0)
    return _client


async def fetch_channel_videos(channel_id: str) -> list[dict]:
    """Fetch per-video stats (title, views, likes, comments) for a channel."""
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY not configured")

    client = _get_client()

    # Get the uploads playlist ID
    resp = await client.get(f"{YT_API_BASE}/channels", params={
        "part": "contentDetails",
        "id": channel_id,
        "key": API_KEY,
    })
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        logger.warning("YouTube channel %s not found", channel_id)
        return []

    uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # List all videos in the uploads playlist (paginate if >50)
    video_ids: list[str] = []
    page_token: str | None = None
    while True:
        params: dict = {
            "part": "snippet",
            "playlistId": uploads_id,
            "maxResults": 50,
            "key": API_KEY,
        }
        if page_token:
            params["pageToken"] = page_token

        resp = await client.get(f"{YT_API_BASE}/playlistItems", params=params)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("items", []):
            vid = item.get("snippet", {}).get("resourceId", {}).get("videoId")
            if vid:
                video_ids.append(vid)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    if not video_ids:
        return []

    # Fetch video statistics in batches of 50
    rows: list[dict] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        resp = await client.get(f"{YT_API_BASE}/videos", params={
            "part": "statistics,snippet,contentDetails",
            "id": ",".join(batch),
            "key": API_KEY,
        })
        resp.raise_for_status()

        for item in resp.json().get("items", []):
            stats = item.get("statistics", {})
            snippet = item.get("snippet", {})
            content = item.get("contentDetails", {})
            duration_seconds = _parse_duration_seconds(content.get("duration", ""))
            thumbnails = snippet.get("thumbnails", {})
            # Prefer high-resolution if available, fall back through sizes.
            thumb_url = (
                (thumbnails.get("maxres") or {}).get("url")
                or (thumbnails.get("standard") or {}).get("url")
                or (thumbnails.get("high") or {}).get("url")
                or (thumbnails.get("medium") or {}).get("url")
                or (thumbnails.get("default") or {}).get("url")
                or ""
            )
            rows.append({
                "Video id": item.get("id", ""),
                "Video title": snippet.get("title", ""),
                "Published at": snippet.get("publishedAt", ""),
                "Duration seconds": duration_seconds,
                "Thumbnail": thumb_url,
                "Views": int(stats.get("viewCount", "0")),
                "Likes": int(stats.get("likeCount", "0")),
                "Comments": int(stats.get("commentCount", "0")),
            })

    return rows


async def fetch_channel_stats(channel_id: str) -> list[dict]:
    """Fetch channel-level stats (subscribers, total views)."""
    if not API_KEY:
        raise ValueError("YOUTUBE_API_KEY not configured")

    client = _get_client()
    resp = await client.get(f"{YT_API_BASE}/channels", params={
        "part": "statistics",
        "id": channel_id,
        "key": API_KEY,
    })
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        logger.warning("YouTube channel %s not found", channel_id)
        return []

    stats = items[0].get("statistics", {})
    return [{
        "Subscribers": int(stats.get("subscriberCount", "0")),
        "Views": int(stats.get("viewCount", "0")),
    }]
