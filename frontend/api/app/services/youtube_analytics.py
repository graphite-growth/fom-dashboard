"""YouTube Analytics API client — fetches daily subscriber gained/lost.

Uses OAuth refresh-token auth (channel owner consent) — distinct from youtube.py,
which uses a public API key for current channel/video stats. The Analytics API
exposes historical daily metrics (subscribersGained, subscribersLost) that the
public Data API does not.
"""

import logging
import os
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

YT_ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"
TOKEN_URI = "https://oauth2.googleapis.com/token"

CLIENT_ID = os.environ.get("YOUTUBE_OAUTH_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("YOUTUBE_OAUTH_CLIENT_SECRET", "")
REFRESH_TOKEN = os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN", "")

_credentials: Credentials | None = None


def _get_credentials() -> Credentials:
    """Return cached, refreshed OAuth credentials."""
    global _credentials
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        raise ValueError(
            "YouTube Analytics OAuth not configured: set "
            "YOUTUBE_OAUTH_CLIENT_ID, YOUTUBE_OAUTH_CLIENT_SECRET, "
            "YOUTUBE_OAUTH_REFRESH_TOKEN"
        )
    if _credentials is None:
        _credentials = Credentials(
            token=None,
            refresh_token=REFRESH_TOKEN,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            token_uri=TOKEN_URI,
        )
    if not _credentials.valid:
        _credentials.refresh(Request())
    return _credentials


async def fetch_subscriber_deltas(
    channel_id: str, start_date: str, end_date: str
) -> list[dict[str, Any]]:
    """Daily subscribersGained/subscribersLost for the channel, ascending by day.

    Returns rows like {"date": "2026-04-21", "gained": 12, "lost": 3, "net": 9}.
    Days with no activity are omitted by the API (caller should default to 0).

    Uses ``channel==MINE`` rather than ``channel==<id>``: the latter requires
    a content-owner (MCN) credential, the former works for regular channel
    managers. The channel queried is implicitly the YouTube identity selected
    during OAuth, so ``channel_id`` is taken on trust here.
    """
    creds = _get_credentials()

    async with httpx.AsyncClient(timeout=30.0) as client:
        identity_resp = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "snippet", "mine": "true"},
            headers={"Authorization": f"Bearer {creds.token}"},
        )
        if identity_resp.is_success:
            items = identity_resp.json().get("items", [])
            if items:
                resolved_id = items[0].get("id", "<unknown>")
                resolved_title = items[0].get("snippet", {}).get("title", "<unknown>")
                if resolved_id != channel_id:
                    logger.warning(
                        "OAuth resolved to channel %s (%s) — expected %s",
                        resolved_title, resolved_id, channel_id,
                    )
                else:
                    logger.info("OAuth identity confirmed: %s (%s)", resolved_title, resolved_id)
            else:
                logger.warning("OAuth identity has no YouTube channel (mine=true returned empty)")

        resp = await client.get(
            f"{YT_ANALYTICS_BASE}/reports",
            params={
                "ids": "channel==MINE",
                "startDate": start_date,
                "endDate": end_date,
                "metrics": "subscribersGained,subscribersLost",
                "dimensions": "day",
                "sort": "day",
            },
            headers={"Authorization": f"Bearer {creds.token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    rows: list[dict[str, Any]] = []
    for row in data.get("rows", []):
        date, gained, lost = row[0], int(row[1]), int(row[2])
        rows.append({"date": date, "gained": gained, "lost": lost, "net": gained - lost})
    return rows
