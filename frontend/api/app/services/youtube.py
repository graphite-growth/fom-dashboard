"""YouTube Data API v3 client — replaces Supermetrics YTPD connector."""

import logging
import os

import httpx

logger = logging.getLogger(__name__)

YT_API_BASE = "https://www.googleapis.com/youtube/v3"
API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

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
            "part": "statistics,snippet",
            "id": ",".join(batch),
            "key": API_KEY,
        })
        resp.raise_for_status()

        for item in resp.json().get("items", []):
            stats = item.get("statistics", {})
            rows.append({
                "Video title": item.get("snippet", {}).get("title", ""),
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
