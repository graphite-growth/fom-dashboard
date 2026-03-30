"""Supermetrics REST API client."""

import json
import logging

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://api.supermetrics.com/enterprise/v2/query/data/json"


async def query(
    api_key: str,
    ds_id: str,
    fields: str,
    *,
    ds_accounts: str | None = None,
    date_range_type: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    settings: dict | None = None,
    max_rows: int = 5000,
) -> list[list]:
    """Run a Supermetrics query and return rows (first row = headers)."""
    payload: dict = {
        "ds_id": ds_id,
        "fields": fields,
        "max_rows": max_rows,
    }
    if ds_accounts:
        payload["ds_accounts"] = ds_accounts
    if date_range_type:
        payload["date_range_type"] = date_range_type
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    if settings:
        payload["settings"] = settings

    params = {"json": json.dumps(payload)}
    headers = {"Authorization": f"Bearer {api_key}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(BASE_URL, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    rows = data.get("data", [])
    if not rows:
        logger.warning("Supermetrics query returned no data for ds_id=%s", ds_id)
    return rows
