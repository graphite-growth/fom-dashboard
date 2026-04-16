"""Dashboard data endpoint."""

import logging
import os

from fastapi import APIRouter, Depends, Header
from starlette.responses import JSONResponse

from app.auth import get_current_user
from app.services.dashboard import get_dashboard_data

logger = logging.getLogger(__name__)

INTERNAL_SECRET = os.environ.get("AUTH_SECRET", "")

router = APIRouter()


@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)) -> JSONResponse:
    """Return live dashboard data from Supermetrics. Requires authentication."""
    return await _get_data()


@router.get("/dashboard/internal")
async def dashboard_internal(x_internal_secret: str = Header(default="")) -> JSONResponse:
    """Internal endpoint for server-side calls. Authenticated via shared secret."""
    if not x_internal_secret or x_internal_secret != INTERNAL_SECRET:
        return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
    return await _get_data()


async def _get_data() -> JSONResponse:
    try:
        data = await get_dashboard_data()
        return JSONResponse(content=data)
    except Exception:
        logger.exception("Failed to fetch dashboard data")
        return JSONResponse(
            content={"error": "Failed to fetch dashboard data"},
            status_code=503,
        )
