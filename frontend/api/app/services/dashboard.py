"""Dashboard data service — fetches from Google Ads and YouTube APIs, transforms, and caches."""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

from app.services import google_ads, youtube, youtube_analytics

logger = logging.getLogger(__name__)

# Configuration with defaults
GOOGLE_ADS_ACCOUNT_ID = os.environ.get("GOOGLE_ADS_ACCOUNT_ID", "6759019449")
YOUTUBE_CHANNEL_ID = os.environ.get("YOUTUBE_CHANNEL_ID", "UCjoo243IaOdidaL8SA7_-HQ")
DASHBOARD_BUDGET = float(os.environ.get("DASHBOARD_BUDGET", "1940"))
DASHBOARD_FLIGHT_START = os.environ.get("DASHBOARD_FLIGHT_START", "2026-03-24")
DASHBOARD_FLIGHT_END = os.environ.get("DASHBOARD_FLIGHT_END", "2026-04-30")
# All campaigns whose name starts with this prefix are aggregated on the Subscribers tab
# and excluded from Overview totals/demographics. Add a new "FOM - Subscribers - X" campaign
# in Google Ads and it picks up the right tab automatically.
SUBSCRIBERS_CAMPAIGN_PREFIX = "FOM - Subscribers - "
SUBSCRIBERS_CAMPAIGN_START = "2026-04-21"

# FOM Google Ads account is configured to America/Chicago. Match the account's
# timezone so subscriber snapshots and the daily-views chart agree on what "today" is.
ACCOUNT_TZ = ZoneInfo("America/Chicago")


def _is_subs_campaign(name: object) -> bool:
    return isinstance(name, str) and name.startswith(SUBSCRIBERS_CAMPAIGN_PREFIX)

# Simple TTL cache
_cache: dict[str, Any] | None = None
_cache_time: float = 0
CACHE_TTL = 900  # 15 minutes


def _build_subscriber_history(
    deltas: list[dict[str, Any]],
    current_subscribers: int,
    start_date: str,
    end_date: str,
) -> list[dict[str, Any]]:
    """Build daily {date, subscribers} series, anchored to today's count.

    Anchors end_date subscriber count to current_subscribers (from YouTube Data API)
    and walks backwards subtracting each day's net (gained - lost) to recover
    historical end-of-day totals.
    """
    if current_subscribers <= 0:
        return []

    net_by_date = {row["date"]: int(row["net"]) for row in deltas}

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

    history: list[dict[str, Any]] = []
    running_total = current_subscribers
    cursor = end_dt
    while cursor >= start_dt:
        date_str = cursor.strftime("%Y-%m-%d")
        history.append({"date": date_str, "subscribers": running_total})
        running_total -= net_by_date.get(date_str, 0)
        cursor -= timedelta(days=1)

    history.reverse()
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


# Ad group display name mapping — cleans inconsistent Google Ads names for the dashboard.
AD_GROUP_DISPLAY_NAMES: dict[str, str] = {
    "Ad Group 1: Company Size + Marketing Interests": "Company Size + Interests",
    "Ad Group 2: Channel Premium Whitelist": "Channel Premium Whitelist",
    "Ad Group 3: Custom Intent Search Behavior": "Custom Intent Search",
    "AG4 - Retargeting": "Retargeting Website Visitors",
    "AG4 - Retargeting graphite.io visitors": "Retargeting Website Visitors",
    "AG5 - Retargeting 50% viewers": "Retargeting 50% Viewers",
}

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
    """Aggregate by label, excluding the subscribers campaign so demographics are video-ads only."""
    filtered = [r for r in rows if not _is_subs_campaign(r.get("Campaign name"))]
    agg: dict[str, dict[str, float]] = {}
    for r in filtered:
        raw_label = r.get(label_key, "Unknown")
        label = label_map.get(raw_label, raw_label) if label_map else raw_label
        if label not in agg:
            agg[label] = {"views": 0, "cost": 0.0, "impressions": 0}
        agg[label]["views"] += int(r.get("Video views", 0))
        agg[label]["cost"] += float(r.get("Cost (USD)", 0))
        agg[label]["impressions"] += int(r.get("Impressions", 0))

    total_views = sum(d["views"] for d in agg.values())
    result = [
        {
            "label": label,
            "views": int(d["views"]),
            "cost": round(d["cost"], 2),
            "impressions": int(d["impressions"]),
            "pctOfViews": round(d["views"] / total_views, 4) if total_views > 0 else 0,
        }
        for label, d in agg.items()
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

    ad_daily: list[dict[str, Any]] = [
        {
            "date": d,
            "cost": round(v["cost"], 2),
            "impressions": int(v["impressions"]),
        }
        for d, v in sorted(subs_daily_agg.items())
        if d >= SUBSCRIBERS_CAMPAIGN_START
    ]

    sorted_history = sorted(subscriber_history, key=lambda x: x["date"])
    new_subs_by_date: dict[str, int] = {}
    for prev, curr in zip(sorted_history, sorted_history[1:]):
        if curr["date"] >= SUBSCRIBERS_CAMPAIGN_START:
            new_subs_by_date[curr["date"]] = curr["subscribers"] - prev["subscribers"]

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
    subscriber_deltas: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Transform Supermetrics data into DashboardData shape."""
    # Subscribers campaign rows are partitioned out — they live on their own tab.
    subs_ads_rows = [r for r in ads_rows if _is_subs_campaign(r.get("Campaign name"))]
    video_ads_rows = [r for r in ads_rows if not _is_subs_campaign(r.get("Campaign name"))]
    # Group Google Ads data by ad name (episode), then ad group
    episodes: dict[str, dict[str, Any]] = {}
    for row in video_ads_rows:
        ad_name = row.get("Image ad name", row.get("Ad name", ""))
        adgroup_raw = row.get("Ad group name", row.get("Ad group", "Unknown"))
        adgroup = AD_GROUP_DISPLAY_NAMES.get(adgroup_raw, adgroup_raw)
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
        if date not in target:
            target[date] = {"views": 0, "cost": 0.0, "impressions": 0}
        target[date]["views"] += int(row.get("Video views", 0))
        target[date]["cost"] += float(row.get("Cost (USD)", row.get("Cost", 0)))
        target[date]["impressions"] += int(row.get("Impressions", 0))

    daily = [{"date": d, "views": int(v["views"]), "cost": round(v["cost"], 2)} for d, v in sorted(daily_agg.items())]

    # Channel stats
    subscribers = 0
    if channel_stats:
        row = channel_stats[0]
        subscribers = int(row.get("Subscribers", 0))

    # Total public views from per-video data (excludes Shorts counted in channel-level stat)
    total_channel_views = sum(int(r.get("Views", 0)) for r in ytpd_rows)

    # Reconstruct daily subscriber history from YouTube Analytics deltas,
    # anchored to the current count from the YouTube Data API.
    today = datetime.now(ACCOUNT_TZ).strftime("%Y-%m-%d")
    subscriber_history = _build_subscriber_history(
        subscriber_deltas or [], subscribers, DASHBOARD_FLIGHT_START, today
    )

    # Projections: budget / CPV = projected views
    total_paid_views = sum(v["views"] for v in videos)
    total_cost = sum(v["cost"] for v in videos)
    total_public_views = sum(v.get("publicViews", 0) for v in videos)

    avg_cpv = total_cost / total_paid_views if total_paid_views > 0 else 0.03
    projected_paid_views = round(DASHBOARD_BUDGET / avg_cpv) if avg_cpv > 0 else 0

    # Project public views at the same ratio as current organic/paid
    organic_ratio = total_public_views / total_paid_views if total_paid_views > 0 else 1.0
    projected_public_views = round(projected_paid_views * organic_ratio)

    subscribers_campaign = _build_subscribers_campaign(
        subs_ads_rows, subs_daily_agg, subscriber_history
    )

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
    """Fetch dashboard data from Google Ads and YouTube APIs with caching."""
    global _cache, _cache_time

    now = time.time()
    if _cache is not None and (now - _cache_time) < CACHE_TTL:
        logger.info("Returning cached dashboard data")
        return _cache

    today = datetime.now(ACCOUNT_TZ).strftime("%Y-%m-%d")

    # Fetch all data in parallel from Google Ads REST API and YouTube Data API
    results = await asyncio.gather(
        google_ads.fetch_ad_performance(GOOGLE_ADS_ACCOUNT_ID, DASHBOARD_FLIGHT_START, today),
        google_ads.fetch_daily_breakdown(GOOGLE_ADS_ACCOUNT_ID, DASHBOARD_FLIGHT_START, today),
        youtube.fetch_channel_videos(YOUTUBE_CHANNEL_ID),
        youtube.fetch_channel_stats(YOUTUBE_CHANNEL_ID),
        google_ads.fetch_age_demographics(GOOGLE_ADS_ACCOUNT_ID, DASHBOARD_FLIGHT_START, today),
        google_ads.fetch_gender_demographics(GOOGLE_ADS_ACCOUNT_ID, DASHBOARD_FLIGHT_START, today),
        google_ads.fetch_device_demographics(GOOGLE_ADS_ACCOUNT_ID, DASHBOARD_FLIGHT_START, today),
        google_ads.fetch_geo_demographics(GOOGLE_ADS_ACCOUNT_ID, DASHBOARD_FLIGHT_START, today),
        youtube_analytics.fetch_subscriber_deltas(YOUTUBE_CHANNEL_ID, DASHBOARD_FLIGHT_START, today),
        return_exceptions=True,
    )

    # Unpack results, replacing exceptions with empty lists
    unpacked: list[list[dict]] = []
    labels = [
        "ads", "daily", "youtube_videos", "youtube_channel",
        "age", "gender", "device", "geo", "subscriber_deltas",
    ]
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            logger.error("Query %s failed: %s", labels[i], r)
            unpacked.append([])
        else:
            unpacked.append(r)

    (
        ads_rows, ads_daily_rows, ytpd_rows, channel_stats,
        age_rows, gender_rows, device_rows, geo_rows,
        subscriber_deltas,
    ) = unpacked

    demographics = _transform_demographics(age_rows, gender_rows, device_rows, geo_rows)

    result = _transform(ads_rows, ads_daily_rows, ytpd_rows, channel_stats, subscriber_deltas)
    result["demographics"] = demographics

    _cache = result
    _cache_time = now
    logger.info("Dashboard data refreshed and cached")

    return result
