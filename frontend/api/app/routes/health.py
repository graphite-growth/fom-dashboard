import os
import traceback

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/diag")
async def diagnostics() -> dict:
    """Temporary diagnostic endpoint to debug Vercel deployment."""
    result: dict = {
        "env": {
            k: ("set" if os.environ.get(k) else "missing")
            for k in [
                "GOOGLE_ADS_DEVELOPER_TOKEN",
                "GOOGLE_ADS_CLIENT_ID",
                "GOOGLE_ADS_CLIENT_SECRET",
                "GOOGLE_ADS_REFRESH_TOKEN",
                "GOOGLE_ADS_LOGIN_CUSTOMER_ID",
                "YOUTUBE_API_KEY",
            ]
        },
    }

    # Test google-ads import
    try:
        from google.ads.googleads.client import GoogleAdsClient  # noqa: F401
        result["google_ads_import"] = "ok"
    except Exception as e:
        result["google_ads_import"] = f"FAILED: {e}"

    # Test a simple query
    try:
        from app.services import google_ads
        import asyncio
        rows = await google_ads.fetch_daily_breakdown(
            os.environ.get("GOOGLE_ADS_ACCOUNT_ID", "6759019449"),
            "2026-04-15", "2026-04-16",
        )
        result["google_ads_query"] = f"ok, {len(rows)} rows"
    except Exception as e:
        result["google_ads_query"] = f"FAILED: {traceback.format_exc()[-500:]}"

    return result
