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
DASHBOARD_BUDGET = float(os.environ.get("DASHBOARD_BUDGET", "1940"))
DASHBOARD_FLIGHT_START = os.environ.get("DASHBOARD_FLIGHT_START", "2026-03-24")
DASHBOARD_FLIGHT_END = os.environ.get("DASHBOARD_FLIGHT_END", "2026-04-30")
# All campaigns whose name starts with this prefix are aggregated on the Subscribers tab
# and excluded from Overview totals/demographics.
SUBSCRIBERS_CAMPAIGN_PREFIX = "FOM - Subscribers - "
SUBSCRIBERS_CAMPAIGN_START = "2026-04-21"


def _is_subs_campaign(name: object) -> bool:
    return isinstance(name, str) and name.startswith(SUBSCRIBERS_CAMPAIGN_PREFIX)

# Simple TTL cache
_cache: dict[str, Any] | None = None
_cache_time: float = 0
CACHE_TTL = 900  # 15 minutes

# In-memory subscriber history (serverless filesystem is read-only)
_subscriber_history: list[dict[str, Any]] | None = None

SUBSCRIBER_SEED = [
    {"date": "2026-03-24", "subscribers": 46},
    {"date": "2026-03-25", "subscribers": 47},
    {"date": "2026-03-26", "subscribers": 47},
    {"date": "2026-03-27", "subscribers": 48},
    {"date": "2026-03-28", "subscribers": 49},
    {"date": "2026-03-29", "subscribers": 49},
    {"date": "2026-03-30", "subscribers": 50},
    {"date": "2026-03-31", "subscribers": 51},
    {"date": "2026-04-01", "subscribers": 52},
]


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

# Manual overrides for ads that can't be matched by name.
# Maps lowercase display name → substring to find in YouTube video title.
MANUAL_TITLE_MATCHES: dict[str, str] = {
    "intro": "why authenticity beats automati",
}


def _match_ytpd_row(video_name: str, ytpd_data: list[dict]) -> dict | None:
    """Match a Google Ads ad name to a YouTube public data row by guest or company name."""
    # 0. Check manual overrides by display name
    _, display = video_name.split(" - ", 1) if " - " in video_name else ("", video_name)
    title_substr = MANUAL_TITLE_MATCHES.get(display.strip().lower())
    if title_substr:
        for yt_row in ytpd_data:
            title = yt_row.get("Video title", "").lower()
            if title_substr in title:
                return yt_row

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


DEVICE_LABELS = {
    "Mobile devices with full browsers": "Mobile",
    "Tablets with full browsers": "Tablet",
    "Computers": "Desktop",
    "Devices streaming video content to TV screens": "TV",
}


def _build_demographic_rows(rows: list[dict], label_key: str, label_map: dict | None = None) -> list[dict]:
    """Aggregate demographic rows by label, excluding the subscribers campaign."""
    filtered = [r for r in rows if not _is_subs_campaign(r.get("Campaign name"))]
    agg: dict[str, dict[str, float]] = {}
    for r in filtered:
        raw_label = r.get(label_key, "Unknown")
        label = label_map.get(raw_label, raw_label) if label_map else raw_label
        bucket = agg.setdefault(label, {"views": 0, "cost": 0.0, "impressions": 0})
        bucket["views"] += int(r.get("Video views", 0))
        bucket["cost"] += float(r.get("Cost (USD)", 0))
        bucket["impressions"] += int(r.get("Impressions", 0))
    total_views = sum(b["views"] for b in agg.values())
    result = [
        {
            "label": label,
            "views": int(b["views"]),
            "cost": round(b["cost"], 2),
            "impressions": int(b["impressions"]),
            "pctOfViews": round(b["views"] / total_views, 4) if total_views > 0 else 0,
        }
        for label, b in agg.items()
    ]
    result.sort(key=lambda x: x["views"], reverse=True)
    return result


def _transform_demographics(
    age_rows: list[dict],
    gender_rows: list[dict],
    device_rows: list[dict],
    geo_rows: list[dict],
) -> dict[str, list[dict]]:
    """Transform raw demographic data into structured format."""
    return {
        "age": _build_demographic_rows(age_rows, "Age"),
        "gender": _build_demographic_rows(gender_rows, "Gender"),
        "device": _build_demographic_rows(device_rows, "Device", DEVICE_LABELS),
        "geo": _build_demographic_rows(geo_rows, "Metro area"),
    }


def _build_subscribers_campaign(
    subs_ads_rows: list[dict],
    subs_daily_agg: dict[str, dict[str, float]],
    subscriber_history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the subscribers-campaign payload: totals + daily new-subs series."""
    cost = round(sum(float(r.get("Cost (USD)", 0)) for r in subs_ads_rows), 2)
    impressions = sum(int(r.get("Impressions", 0)) for r in subs_ads_rows)

    # Daily ad spend / impressions, restricted to campaign window
    ad_daily: list[dict[str, Any]] = [
        {
            "date": d,
            "cost": round(v["cost"], 2),
            "impressions": int(v["impressions"]),
        }
        for d, v in sorted(subs_daily_agg.items())
        if d >= SUBSCRIBERS_CAMPAIGN_START
    ]

    # New-subs-per-day from channel history: diff consecutive days in window.
    # We need the day before each target date to compute its delta.
    sorted_history = sorted(subscriber_history, key=lambda x: x["date"])
    new_subs_by_date: dict[str, int] = {}
    for prev, curr in zip(sorted_history, sorted_history[1:]):
        if curr["date"] >= SUBSCRIBERS_CAMPAIGN_START:
            new_subs_by_date[curr["date"]] = curr["subscribers"] - prev["subscribers"]

    # Subs gained: latest - last snapshot at or before campaign start
    subs_gained = 0
    in_window = [s for s in sorted_history if s["date"] >= SUBSCRIBERS_CAMPAIGN_START]
    pre_window = [s for s in sorted_history if s["date"] < SUBSCRIBERS_CAMPAIGN_START]
    if in_window:
        baseline = pre_window[-1]["subscribers"] if pre_window else in_window[0]["subscribers"]
        subs_gained = in_window[-1]["subscribers"] - baseline

    daily = [
        {
            "date": d["date"],
            "newSubs": new_subs_by_date.get(d["date"], 0),
            "cost": d["cost"],
            "impressions": d["impressions"],
        }
        for d in ad_daily
    ]
    # Include any history dates in the window that don't have ad data yet
    ad_dates = {d["date"] for d in daily}
    for date, new_subs in new_subs_by_date.items():
        if date not in ad_dates:
            daily.append({"date": date, "newSubs": new_subs, "cost": 0.0, "impressions": 0})
    daily.sort(key=lambda x: x["date"])

    cost_per_sub = round(cost / subs_gained, 2) if subs_gained > 0 else 0.0
    conv_rate = round(subs_gained / impressions, 6) if impressions > 0 else 0.0

    campaign_names = sorted({
        str(r["Campaign name"]) for r in subs_ads_rows if r.get("Campaign name")
    })

    return {
        "campaignNames": campaign_names,
        "campaignStart": SUBSCRIBERS_CAMPAIGN_START,
        "subsGained": subs_gained,
        "cost": cost,
        "impressions": impressions,
        "costPerSub": cost_per_sub,
        "convRate": conv_rate,
        "daily": daily,
    }


def _transform(
    ads_rows: list[dict],
    ads_daily_rows: list[dict],
    ytpd_rows: list[dict],
    channel_stats: list[dict] | None = None,
) -> dict[str, Any]:
    """Transform Supermetrics data into DashboardData shape."""
    # Group Google Ads data by ad name (episode), then ad group.
    # Subscribers campaign rows are partitioned out — they live on their own tab.
    subs_ads_rows = [r for r in ads_rows if _is_subs_campaign(r.get("Campaign name"))]
    video_ads_rows = [r for r in ads_rows if not _is_subs_campaign(r.get("Campaign name"))]
    episodes: dict[str, dict[str, Any]] = {}
    for row in video_ads_rows:
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

    # Build daily data — split by campaign so subscribers campaign stays isolated
    daily_agg: dict[str, dict[str, float]] = {}
    subs_daily_agg: dict[str, dict[str, float]] = {}
    for row in ads_daily_rows:
        date = row.get("Date", row.get("Day", ""))
        if not date:
            continue
        target = subs_daily_agg if _is_subs_campaign(row.get("Campaign name")) else daily_agg
        bucket = target.setdefault(date, {"views": 0, "cost": 0.0, "impressions": 0})
        bucket["views"] += int(row.get("Video views", 0))
        bucket["cost"] += float(row.get("Cost (USD)", row.get("Cost", 0)))
        bucket["impressions"] += int(row.get("Impressions", 0))

    daily = [{"date": d, "views": int(v["views"]), "cost": round(v["cost"], 2)} for d, v in sorted(daily_agg.items())]

    # Channel stats
    subscribers = 0
    if channel_stats:
        row = channel_stats[0]
        subscribers = int(row.get("Subscribers", 0))

    # Total public views from long-form videos only (exclude Shorts by filtering < 60s).
    # YTPD doesn't return duration, so we exclude known Shorts by title prefix "#shorts"
    # or short titles. For now, sum all per-video views from YTPD as a closer proxy than
    # the channel-level stat which includes Shorts.
    total_channel_views = sum(int(r.get("Views", 0)) for r in ytpd_rows)

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

    subscribers_campaign = _build_subscribers_campaign(subs_ads_rows, subs_daily_agg, subscriber_history)

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
        "subscribersCampaign": subscribers_campaign,
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

    # Fetch Google Ads daily breakdown (with campaign for splitting)
    ads_daily_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="AW",
        ds_accounts=GOOGLE_ADS_ACCOUNT_ID,
        fields="Date,Campaignname,videoviews,Cost_usd,Impressions",
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

    # Fetch demographics (4 separate queries — different report types)
    age_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="AW",
        ds_accounts=GOOGLE_ADS_ACCOUNT_ID,
        fields="Age,Campaignname,videoviews,Cost_usd,Impressions",
        date_range_type="custom",
        start_date=DASHBOARD_FLIGHT_START,
        end_date=today,
    )
    gender_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="AW",
        ds_accounts=GOOGLE_ADS_ACCOUNT_ID,
        fields="Gender,Campaignname,videoviews,Cost_usd,Impressions",
        date_range_type="custom",
        start_date=DASHBOARD_FLIGHT_START,
        end_date=today,
    )
    device_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="AW",
        ds_accounts=GOOGLE_ADS_ACCOUNT_ID,
        fields="Device,Campaignname,videoviews,Cost_usd,Impressions",
        date_range_type="custom",
        start_date=DASHBOARD_FLIGHT_START,
        end_date=today,
    )
    geo_raw = await supermetrics.query(
        api_key=SUPERMETRICS_API_KEY,
        ds_id="AW",
        ds_accounts=GOOGLE_ADS_ACCOUNT_ID,
        fields="Metroarea,Campaignname,videoviews,Cost_usd,Impressions",
        date_range_type="custom",
        start_date=DASHBOARD_FLIGHT_START,
        end_date=today,
    )

    ads_rows = _rows_to_dicts(ads_rows_raw)
    ads_daily_rows = _rows_to_dicts(ads_daily_raw)
    ytpd_rows = _rows_to_dicts(ytpd_rows_raw)
    channel_stats = _rows_to_dicts(channel_stats_raw)

    demographics = _transform_demographics(
        _rows_to_dicts(age_raw),
        _rows_to_dicts(gender_raw),
        _rows_to_dicts(device_raw),
        _rows_to_dicts(geo_raw),
    )

    result = _transform(ads_rows, ads_daily_rows, ytpd_rows, channel_stats)
    result["demographics"] = demographics

    _cache = result
    _cache_time = now
    logger.info("Dashboard data refreshed and cached")

    return result
