"""Load secrets from AWS SSM Parameter Store into environment variables.

When a prefix is provided (e.g., "/my-project"), all SecureString parameters
under that path are fetched and injected into os.environ. This keeps secrets
out of plaintext EB environment variables.

In local development the prefix is empty, so secrets come from the regular
environment (e.g., .env file or shell exports).
"""

import logging
import os

logger = logging.getLogger(__name__)


def _fetch_parameters(prefix: str, region: str) -> dict[str, str]:
    """Fetch all SSM parameters under prefix, returning {name: value}."""
    import boto3

    ssm = boto3.client("ssm", region_name=region)
    params: dict[str, str] = {}
    pages = ssm.get_paginator("get_parameters_by_path")
    for page in pages.paginate(Path=prefix, WithDecryption=True):
        for p in page["Parameters"]:
            # "/my-project/AUTH_SECRET" -> "AUTH_SECRET"
            name = p["Name"].rsplit("/", 1)[-1]
            params[name] = p["Value"]
    return params


def load_ssm_parameters(prefix: str, region: str) -> None:
    """Load SSM secrets into os.environ. No-op when prefix is empty."""
    if not prefix:
        return

    for key, value in _fetch_parameters(prefix, region).items():
        os.environ.setdefault(key, value)
        logger.info("Loaded secret %s from SSM", key)
