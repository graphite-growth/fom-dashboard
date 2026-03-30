"""Secrets loading — Vercel uses environment variables directly, no SSM needed."""

import logging

logger = logging.getLogger(__name__)


def load_ssm_parameters(prefix: str, region: str) -> None:
    """No-op on Vercel. Secrets come from Vercel environment variables."""
    pass
