"""Dashboard data endpoint."""

import logging

from fastapi import APIRouter, Depends
from starlette.responses import JSONResponse

from app.auth import get_current_user
from app.services.dashboard import get_dashboard_data

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard")
async def dashboard(user: dict = Depends(get_current_user)) -> JSONResponse:
    """Return live dashboard data from Supermetrics. Requires authentication."""
    try:
        data = await get_dashboard_data()
        return JSONResponse(content=data)
    except Exception:
        logger.error("Failed to fetch dashboard data")
        return JSONResponse(
            content={"error": "Failed to fetch dashboard data"},
            status_code=503,
        )
