"""Best-effort keep-alive ping for the Render-hosted cosigner service.

The cosigner runs on Render's free tier, which spins down after ~15 min of
inactivity. A cold start takes 30-60s and would block a live /cosign call.
This module issues fire-and-forget GET /health pings to keep it warm while
players are connected, so the cold start is absorbed during quiet time.
"""

import logging

import httpx
from django.conf import settings
from twisted.internet import threads

logger = logging.getLogger(__name__)


def _blocking_ping():
    """Sync GET /health. Runs on a worker thread via deferToThread."""
    if not getattr(settings, "XRPL_MULTISIG_ENABLED", False):
        return
    url = (getattr(settings, "XRPL_COSIGNER_URL", "") or "").rstrip("/")
    if not url:
        return
    try:
        resp = httpx.get(f"{url}/health", timeout=30.0)
        logger.debug("Cosigner keep-alive: %s %s", resp.status_code, url)
    except Exception as e:
        logger.debug("Cosigner keep-alive failed (non-fatal): %s", e)


def warm_cosigner():
    """Fire-and-forget keep-alive ping. Safe to call from the reactor thread."""
    threads.deferToThread(_blocking_ping)
