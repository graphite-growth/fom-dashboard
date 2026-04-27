"""Google Ads API client using the google-ads library (gRPC)."""

import asyncio
import logging
import os

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

logger = logging.getLogger(__name__)

# Credentials from environment
_config = {
    "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", ""),
    "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID", ""),
    "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET", ""),
    "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN", ""),
    "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", ""),
    "use_proto_plus": True,
}

# Lazy-initialized client (reused across warm invocations)
_client: GoogleAdsClient | None = None


def _get_client() -> GoogleAdsClient:
    global _client
    if _client is None:
        _client = GoogleAdsClient.load_from_dict(_config)
    return _client


# --- Row parsing (adapted from director/tools/gaql.py) ---

def _safe_value(val: object) -> object:
    """Convert a protobuf value to a JSON-safe Python type."""
    # Check for proto_plus enums first (they subclass int, so isinstance(int) would catch them)
    if not isinstance(val, (str, bytes)) and hasattr(val, "name") and hasattr(val, "value"):
        return val.name
    if isinstance(val, (str, int, float, bool)):
        return val
    try:
        return str(val)
    except Exception:
        return None


def _parse_row(row: object, fields: list[str]) -> dict:
    """Parse a GAQL protobuf row into a flat dict."""
    result = {}
    for field in fields:
        try:
            obj = row
            for part in field.strip().split("."):
                obj = getattr(obj, part)
            if field.endswith("_micros"):
                result[field] = obj
                result[field.replace("_micros", "")] = round(obj / 1_000_000, 2)
            else:
                result[field] = _safe_value(obj)
        except AttributeError:
            result[field] = None
    return result


def _extract_fields(query: str) -> list[str]:
    """Extract field names from a GAQL SELECT query."""
    upper = query.upper()
    select_idx = upper.index("SELECT") + 6
    from_idx = upper.index("FROM")
    fields_str = query[select_idx:from_idx].strip()
    return [f.strip() for f in fields_str.split(",")]


def _run_query(query: str, customer_id: str) -> list[dict]:
    """Execute a GAQL query synchronously (runs in thread pool for async)."""
    client = _get_client()
    service = client.get_service("GoogleAdsService")
    response = service.search(customer_id=customer_id, query=query)
    fields = _extract_fields(query)
    return [_parse_row(row, fields) for row in response]


async def _query(query: str, customer_id: str) -> list[dict]:
    """Execute a GAQL query asynchronously via thread pool."""
    return await asyncio.to_thread(_run_query, query, customer_id)


# --- Enum label mappings ---

AGE_RANGE_LABELS = {
    "AGE_RANGE_18_24": "18-24",
    "AGE_RANGE_25_34": "25-34",
    "AGE_RANGE_35_44": "35-44",
    "AGE_RANGE_45_54": "45-54",
    "AGE_RANGE_55_64": "55-64",
    "AGE_RANGE_65_UP": "65+",
    "AGE_RANGE_UNDETERMINED": "Undetermined",
}

GENDER_LABELS = {
    "MALE": "Male",
    "FEMALE": "Female",
    "UNDETERMINED": "Undetermined",
}

DEVICE_LABELS = {
    "MOBILE": "Mobile devices with full browsers",
    "TABLET": "Tablets with full browsers",
    "DESKTOP": "Computers",
    "CONNECTED_TV": "Devices streaming video content to TV screens",
    "OTHER": "Other",
}


# --- Query functions ---

async def fetch_ad_performance(
    customer_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Fetch ad-level performance data (views, cost, impressions, quartiles).

    Includes the FOM Subscribers Demand Gen campaign so its cost/impressions
    are pulled even though it isn't a VIDEO channel type.
    """
    query = f"""
        SELECT
            campaign.name,
            ad_group.name,
            ad_group_ad.ad.name,
            metrics.video_trueview_views,
            metrics.cost_micros,
            metrics.impressions,
            metrics.video_quartile_p25_rate,
            metrics.video_quartile_p50_rate,
            metrics.video_quartile_p75_rate,
            metrics.video_quartile_p100_rate
        FROM ad_group_ad
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            AND (campaign.advertising_channel_type = 'VIDEO'
                OR campaign.name = 'FOM - Subscribers - Company Size + Interests')
            AND metrics.impressions > 0
    """
    raw = await _query(query, customer_id)
    return [
        {
            "Campaign name": r.get("campaign.name", ""),
            "Ad group name": r.get("ad_group.name", ""),
            "Image ad name": r.get("ad_group_ad.ad.name", ""),
            "Video views": r.get("metrics.video_trueview_views", 0),
            "Cost (USD)": r.get("metrics.cost", 0.0),
            "Impressions": r.get("metrics.impressions", 0),
            "Watch 25% rate": r.get("metrics.video_quartile_p25_rate", 0.0),
            "Watch 50% rate": r.get("metrics.video_quartile_p50_rate", 0.0),
            "Watch 75% rate": r.get("metrics.video_quartile_p75_rate", 0.0),
            "Watch 100% rate": r.get("metrics.video_quartile_p100_rate", 0.0),
        }
        for r in raw
    ]


async def fetch_daily_breakdown(
    customer_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Fetch daily views, cost, impressions per campaign."""
    query = f"""
        SELECT
            segments.date,
            campaign.name,
            metrics.video_trueview_views,
            metrics.cost_micros,
            metrics.impressions
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            AND (campaign.advertising_channel_type = 'VIDEO'
                OR campaign.name = 'FOM - Subscribers - Company Size + Interests')
    """
    raw = await _query(query, customer_id)
    return [
        {
            "Date": r.get("segments.date", ""),
            "Campaign name": r.get("campaign.name", ""),
            "Video views": r.get("metrics.video_trueview_views", 0),
            "Cost (USD)": r.get("metrics.cost", 0.0),
            "Impressions": r.get("metrics.impressions", 0),
        }
        for r in raw
    ]


async def fetch_age_demographics(
    customer_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Fetch video views by age range."""
    query = f"""
        SELECT
            ad_group_criterion.age_range.type,
            campaign.name,
            metrics.video_trueview_views,
            metrics.cost_micros,
            metrics.impressions
        FROM age_range_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """
    raw = await _query(query, customer_id)
    return [
        {
            "Age": AGE_RANGE_LABELS.get(r.get("ad_group_criterion.age_range.type", ""), "Unknown"),
            "Campaign name": r.get("campaign.name", ""),
            "Video views": r.get("metrics.video_trueview_views", 0),
            "Cost (USD)": r.get("metrics.cost", 0.0),
            "Impressions": r.get("metrics.impressions", 0),
        }
        for r in raw
    ]


async def fetch_gender_demographics(
    customer_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Fetch video views by gender."""
    query = f"""
        SELECT
            ad_group_criterion.gender.type,
            campaign.name,
            metrics.video_trueview_views,
            metrics.cost_micros,
            metrics.impressions
        FROM gender_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
    """
    raw = await _query(query, customer_id)
    return [
        {
            "Gender": GENDER_LABELS.get(r.get("ad_group_criterion.gender.type", ""), "Unknown"),
            "Campaign name": r.get("campaign.name", ""),
            "Video views": r.get("metrics.video_trueview_views", 0),
            "Cost (USD)": r.get("metrics.cost", 0.0),
            "Impressions": r.get("metrics.impressions", 0),
        }
        for r in raw
    ]


async def fetch_device_demographics(
    customer_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Fetch video views by device type."""
    query = f"""
        SELECT
            segments.device,
            campaign.name,
            metrics.video_trueview_views,
            metrics.cost_micros,
            metrics.impressions
        FROM campaign
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            AND campaign.advertising_channel_type = 'VIDEO'
    """
    raw = await _query(query, customer_id)
    return [
        {
            "Device": DEVICE_LABELS.get(r.get("segments.device", ""), r.get("segments.device", "Unknown")),
            "Campaign name": r.get("campaign.name", ""),
            "Video views": r.get("metrics.video_trueview_views", 0),
            "Cost (USD)": r.get("metrics.cost", 0.0),
            "Impressions": r.get("metrics.impressions", 0),
        }
        for r in raw
    ]


async def fetch_geo_demographics(
    customer_id: str, start_date: str, end_date: str,
) -> list[dict]:
    """Fetch video views by metro area (DMA)."""
    query = f"""
        SELECT
            campaign_criterion.location.geo_target_constant,
            campaign.name,
            metrics.video_trueview_views,
            metrics.cost_micros,
            metrics.impressions
        FROM location_view
        WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
            AND campaign.advertising_channel_type = 'VIDEO'
    """
    raw = await _query(query, customer_id)

    # Resolve geo target constant resource names to display names
    geo_names = await _resolve_geo_constants(
        {r.get("campaign_criterion.location.geo_target_constant", "") for r in raw},
        customer_id,
    )

    return [
        {
            "Metro area": geo_names.get(r.get("campaign_criterion.location.geo_target_constant", ""), "Unknown"),
            "Campaign name": r.get("campaign.name", ""),
            "Video views": r.get("metrics.video_trueview_views", 0),
            "Cost (USD)": r.get("metrics.cost", 0.0),
            "Impressions": r.get("metrics.impressions", 0),
        }
        for r in raw
    ]


# Cached geo constant names
_geo_cache: dict[str, str] = {}


async def _resolve_geo_constants(resource_names: set[str], customer_id: str) -> dict[str, str]:
    """Resolve geo target constant resource names to display names."""
    to_resolve = {rn for rn in resource_names if rn and rn not in _geo_cache}
    if to_resolve:
        # Extract IDs from resource names like "geoTargetConstants/1014221"
        ids = []
        for rn in to_resolve:
            parts = rn.split("/")
            if len(parts) == 2:
                ids.append(parts[1])

        if ids:
            id_list = ", ".join(ids)
            query = f"""
                SELECT
                    geo_target_constant.resource_name,
                    geo_target_constant.name
                FROM geo_target_constant
                WHERE geo_target_constant.id IN ({id_list})
            """
            try:
                rows = await _query(query, customer_id)
                for row in rows:
                    rn = row.get("geo_target_constant.resource_name", "")
                    name = row.get("geo_target_constant.name", rn)
                    _geo_cache[rn] = name
            except GoogleAdsException:
                logger.warning("Failed to resolve geo constants, using resource names")
                for rn in to_resolve:
                    _geo_cache[rn] = rn

    return _geo_cache
