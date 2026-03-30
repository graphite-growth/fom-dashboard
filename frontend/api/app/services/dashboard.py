"""Dashboard data service — fetches from Supermetrics, transforms, and caches."""

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import supermetrics

logger = logging.getLogger(__name__)

# Configuration with defaults
SUPERMETRICS_API_KEY = os.environ.get("SUPERMETRICS_API_KEY", "")
GOOGLE_ADS_ACCOUNT_ID = os.environ.get("GOOGLE_ADS_ACCOUNT_ID", "6759019449")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "UCjoo243IaOdidaL8SA7_-HQ")
DASHBOARD_BUDGET = float(os.environ.get("DASHBOARD_BUDGET", "2500"))
DASHBOARD_FLIGHT_START = os.environ.get("DASHBOARD_FLIGHT_START", "2026-03-24")
DASHBOARD_FLIGHT_END = os.environ.get("DASHBOARD_FLIGHT_END", "2026-04-30")

# Simple TTL cache
_cache: dict[str, Any] | None = None
_cache_time: float = 0
CACHE_TTL = 900  # 15 minutes

# In-memory subscriber history (serverless filesystem is read-only)
_subscriber_history: list[dict[str, Any]] | None = None

SUBSCRIBER_SEED = [{"date": "2026-03-24", "subscribers": 46}]


def _load_subscriber_history() -> list[dict[str, Any]]:
    """Load subscriber history from memory, seeding if empty."""
    global _subscriber_history
    if _subscriber_history is not None:
        return _subscriber_history
    # Try loading from filesystem (works in local dev, not on Vercel)
    history_path = Path(os.environ.get("SUBSCRIBER_HISTORY_PATH", "./subscriber_history.json"))
    if history_path.exists():
        try:
            _subscriber_history = json.loads(history_path.read_text())
            return _subscriber_history
        except (json.JSONDecodeError, OSError):
            logger.warning("Failed to read subscriber history, using seed data")
    _subscriber_history = list(SUBSCRIBER_SEED)
    return _subscriber_history


def _save_subscriber_snapshot(date: str, subscribers: int) -> list[dict[str, Any]]:
    """Append today's subscriber count if not already recorded. Returns full history."""
    history = _load_subscriber_history()
    existing_dates = {entry["date"] for entry in history}
    if date not in existing_dates and subscribers > 0:
        history.append({"date": date, "subscribers": subscribers})
        history.sort(key=lambda x: x["date"])
        # Try filesystem write (works locally, gracefully fails on Vercel)
        history_path = Path(os.environ.get("SUBSCRIBER_HISTORY_PATH", "./subscriber_history.json"))
        try:
            history_path.parent.mkdir(parents=True, exist_ok=True)
            history_path.write_text(json.dumps(history, indent=2))
            logger.info("Saved subscriber snapshot: %s = %d", date, subscribers)
        except OSError:
            logger.info("Filesystem read-only, subscriber snapshot kept in memory only")
    return history


def _rows_to_dicts(rows: list[list]) -> list[dict]:
    """Convert Supermetrics rows (first row = headers) to list of dicts."""
    if len(rows) < 2:
        return []
    headers = rows[0]
    return [dict(zip(headers, row)) for row in rows[1:]]


def _extract_parts(ad_name: str) -> tuple[str, str]:
    """Extract company and guest name from ad name like 'AG1 - Webflow - Dave Steer'."""
    parts = ad_name.split(" - ")
    if len(parts) >= 3:
        return parts[1].strip(), parts[2].strip()
    if len(parts) >= 2:
        return parts[1].strip(), ""
    return ad_name, ""


STOP_WORDS = {"fom", "-", "the", "a", "an", "and", "or", "in", "of", "to", "with", "ag1", "ag2", "ag3"}
TITLE_STOP_WORDS = {"the", "a", "an", "and", "or", "in", "of", "to", "with"}


def _match_ytpd_row(video_name: str, ytpd_data: list[dict]) -> dict | None:
    """Match a Google Ads ad name to a YouTube public data row by guest or company name."""
    company, guest = _extract_parts(video_name)

    # 1. Try matching guest name in YouTube title
    if guest:
        guest_words = set(guest.lower().split())
        for yt_row in ytpd_data:
            title = yt_row.get("Video title", "").lower()
            if guest_words and guest_words.issubset(set(title.split())):
                return yt_row

    # 2. Try matching company name in YouTube title
    if company:
        company_lower = company.lower()
        for yt_row in ytpd_data:
            title = yt_row.get("Video title", "").lower()
            if company_lower in title:
                return yt_row

    # 3. Fallback: fuzzy match with at least 2 common significant words
    name_lower = video_name.lower()
    for yt_row in ytpd_data:
        title = yt_row.get("Video title", "").lower()
        video_words = set(name_lower.split()) - STOP_WORDS
        title_words = set(title.split()) - TITLE_STOP_WORDS
        common = video_words & title_words
        if len(common) >= 2:
            return yt_row
    return None


def _match_public_views(video_name: str, ytpd_data: list[dict]) -> int:
    """Match a Google Ads ad name to YouTube public view data by guest or company name."""
    row = _match_ytpd_row(video_name, ytpd_data)
    return int(row.get("Views", 0)) if row else 0


def _match_engagement(video_name: str, ytpd_data: list[dict]) -> tuple[int, int]:
    """Match a Google Ads ad name to YouTube engagement data. Returns (likes, comments)."""
    row = _match_ytpd_row(video_name, ytpd_data)
    if row is None:
        return 0, 0
    return int(row.get("Likes", 0)), int(row.get("Comments", 0))


def _transform(
    ads_rows: list[dict],
    ads_daily_rows: list[dict],
    ytpd_rows: list[dict],
    channel_stats: list[dict] | None = None,
) -> dict[str, Any]:
    """Transform Supermetrics data into DashboardData shape."""
    # Group Google Ads data by ad name (episode), then ad group
    episodes: dict[str, dict[str, Any]] = {}
    for row in ads_rows:
        ad_name = row.get("Image ad name", row.get("Ad name", ""))
        adgroup = row.get("Ad group name", row.get("Ad group", "Unknown"))
        views = int(row.get("Video views", 0))
        cost = float(row.get("Cost (USD)", row.get("Cost", 0)))
        impressions = int(row.get("Impressions", 0))
        q25 = round(views * float(row.get("Watch 25% rate", 0)))
        q50 = round(views * float(row.get("Watch 50% rate", 0)))
        q75 = round(views * float(row.get("Watch 75% rate", 0)))
        q100 = round(views * float(row.get("Watch 100% rate", 0)))

        # Skip rows without an ad name (shouldn't happen but be safe)
        if not ad_name:
            campaign = row.get("Campaign name", row.get("Campaign", "Unknown"))
            ad_name = campaign

        # Build a friendly display name from ad name
        # "AG1 - Webflow - Dave Steer" -> "Webflow - Dave Steer"
        parts = ad_name.split(" - ", 1)
        display_name = parts[1] if len(parts) > 1 else ad_name

        if display_name not in episodes:
            episodes[display_name] = {
                "name": display_name,
                "raw_name": ad_name,
                "views": 0,
                "cost": 0.0,
                "impressions": 0,
                "q25": 0,
                "q50": 0,
                "q75": 0,
                "q100": 0,
                "adGroups": {},
            }
        c = episodes[display_name]
        c["views"] += views
        c["cost"] += cost
        c["impressions"] += impressions
        c["q25"] += q25
        c["q50"] += q50
        c["q75"] += q75
        c["q100"] += q100

        if adgroup not in c["adGroups"]:
            c["adGroups"][adgroup] = {
                "name": adgroup,
                "views": 0,
                "cost": 0.0,
                "impressions": 0,
                "q25": 0,
                "q50": 0,
                "q75": 0,
                "q100": 0,
            }
        ag = c["adGroups"][adgroup]
        ag["views"] += views
        ag["cost"] += cost
        ag["impressions"] += impressions
        ag["q25"] += q25
        ag["q50"] += q50
        ag["q75"] += q75
        ag["q100"] += q100

    # Build video list
    videos = []
    for c in episodes.values():
        total_views = c["views"]
        total_cost = c["cost"]
        total_impressions = c["impressions"]
        cpv = total_cost / total_views if total_views > 0 else 0
        view_rate = total_views / total_impressions if total_impressions > 0 else 0
        public_views = _match_public_views(c["raw_name"], ytpd_rows)
        likes, comments = _match_engagement(c["raw_name"], ytpd_rows)

        ad_groups = []
        for ag in c["adGroups"].values():
            ag_views = ag["views"]
            ag_cost = ag["cost"]
            ag_impressions = ag["impressions"]
            ad_groups.append(
                {
                    "name": ag["name"],
                    "views": ag_views,
                    "cost": round(ag_cost, 2),
                    "cpv": round(ag_cost / ag_views, 4) if ag_views > 0 else 0,
                    "impressions": ag_impressions,
                    "viewRate": round(ag_views / ag_impressions, 4) if ag_impressions > 0 else 0,
                    "q25": ag["q25"],
                    "q50": ag["q50"],
                    "q75": ag["q75"],
                    "q100": ag["q100"],
                }
            )

        videos.append(
            {
                "name": c["name"],
                "views": total_views,
                "cost": round(total_cost, 2),
                "cpv": round(cpv, 4),
                "impressions": total_impressions,
                "viewRate": round(view_rate, 4),
                "publicViews": public_views,
                "likes": likes,
                "comments": comments,
                "q25": c["q25"],
                "q50": c["q50"],
                "q75": c["q75"],
                "q100": c["q100"],
                "adGroups": ad_groups,
            }
        )

    # Build daily data
    daily_agg: dict[str, dict[str, float]] = {}
    for row in ads_daily_rows:
        date = row.get("Date", row.get("Day", ""))
        if not date:
            continue
        if date not in daily_agg:
            daily_agg[date] = {"views": 0, "cost": 0.0}
        daily_agg[date]["views"] += int(row.get("Video views", 0))
        daily_agg[date]["cost"] += float(row.get("Cost (USD)", row.get("Cost", 0)))

    daily = [{"date": d, "views": int(v["views"]), "cost": round(v["cost"], 2)} for d, v in sorted(daily_agg.items())]

    # Channel stats
    subscribers = 0
    total_channel_views = 0
    if channel_stats:
        row = channel_stats[0]
        subscribers = int(row.get("Subscribers", 0))
        total_channel_views = int(row.get("Views", 0))

    # Save daily subscriber snapshot and load history
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    subscriber_history = _save_subscriber_snapshot(today, subscribers)

    # Projections: budget / CPV = projected views
    total_paid_views = sum(v["views"] for v in videos)
    total_cost = sum(v["cost"] for v in videos)
    total_public_views = sum(v.get("publicViews", 0) for v in videos)

    avg_cpv = total_cost / total_paid_views if total_paid_views > 0 else 0.03
    projected_paid_views = round(DASHBOARD_BUDGET / avg_cpv) if avg_cpv > 0 else 0

    # Project public views at the same ratio as current organic/paid
    organic_ratio = total_public_views / total_paid_views if total_paid_views > 0 else 1.0
    projected_public_views = round(projected_paid_views * organic_ratio)

    return {
        "budget": DASHBOARD_BUDGET,
        "flightStart": DASHBOARD_FLIGHT_START,
        "flightEnd": DASHBOARD_FLIGHT_END,
        "lastUpdated": datetime.now(timezone.utc).isoformat(),
        "organicMultiplier": 1.7,
        "videos": videos,
        "daily": daily,
        "subscribers": subscribers,
        "totalChannelViews": total_channel_views,
        "projectedPaidViews": projected_paid_views,
        "projectedPublicViews": projected_public_views,
        "subscriberHistory": subscriber_history,
    }


async def get_dashboard_data() -> dict[str, Any]:
    """Fetch dashboard data from Supermetrics with caching."""
    global _cache, _cache_time

    now = time.time()
    if _cache is not None and (now - _cache_time) < CACHE_TTL:
        logger.info("Returning cached dashboard data")
        return _cache

    if not SUPERMETRICS_API_KEY:
        raise ValueError("SUPERMETRICS_API_KEY not configured")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch Google Ads campaign/adgroup data
    ads_rows_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="AW",
        ds_accounts=GOOGLE_ADS_ACCOUNT_ID,
        fields="Campaignname,Adgroupname,Imageadname,videoviews,Cost_usd,CostPerVideoView,Impressions,videoviewrate,VideoQuartile25Rate,VideoQuartile50Rate,VideoQuartile75Rate,VideoQuartile100Rate",
        date_range_type="custom",
        start_date=DASHBOARD_FLIGHT_START,
        end_date=today,
    )

    # Fetch Google Ads daily breakdown
    ads_daily_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="AW",
        ds_accounts=GOOGLE_ADS_ACCOUNT_ID,
        fields="Date,videoviews,Cost_usd,Impressions",
        date_range_type="custom",
        start_date=DASHBOARD_FLIGHT_START,
        end_date=today,
    )

    # Fetch YouTube public data (per-video)
    ytpd_rows_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="YTPD",
        fields="channel__videos__details__video_title,channel__videos__details__views,channel__videos__details__likes,channel__videos__details__comments",
        settings={
            "report_type": "channel",
            "YOUTUBE_CHANNEL_ID": YOUTUBE_CHANNEL_ID,
        },
    )

    # Fetch YouTube channel stats (subscribers + total views)
    channel_stats_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="YTPD",
        fields="channels__subscribers,channels__views",
        settings={
            "report_type": "channels",
            "YOUTUBE_CHANNEL_ID": YOUTUBE_CHANNEL_ID,
        },
    )

    ads_rows = _rows_to_dicts(ads_rows_raw)
    ads_daily_rows = _rows_to_dicts(ads_daily_raw)
    ytpd_rows = _rows_to_dicts(ytpd_rows_raw)
    channel_stats = _rows_to_dicts(channel_stats_raw)

    result = _transform(ads_rows, ads_daily_rows, ytpd_rows, channel_stats)

    _cache = result
    _cache_time = now
    logger.info("Dashboard data refreshed and cached")

    return result
