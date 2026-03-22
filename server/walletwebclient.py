"""
Custom WebSocket handler.

Extends Evennia's default WebSocketClient to capture the Cloudflare
CF-IPCountry header on connection open.

The geo country is stored in server_data AFTER super().onOpen() completes,
then re-synced via sessionhandler.sync() so the server session receives it.

super().onOpen() calls init_session() which resets server_data = {}, so any
values set before the super() call are wiped.  Setting after + syncing is the
correct pattern.

In production, Cloudflare injects CF-IPCountry on every WebSocket upgrade
request when the DNS proxy is enabled.  In development, falls back to the
DEV_GEO_COUNTRY Django setting (mirrors the geo middleware behaviour).
"""

from django.conf import settings
from evennia.server.portal.webclient import WebSocketClient
from evennia.utils import logger

logger.log_info("[GEO] walletwebclient.py loaded — WalletWebSocketClient defined")


class WalletWebSocketClient(WebSocketClient):
    """Custom WebSocket client — captures geo-country on connection open."""

    def onOpen(self):
        # Read geo country from Cloudflare header (lowercase — Autobahn
        # normalises HTTP upgrade headers during parsing).
        raw_headers = getattr(self, "http_headers", {}) or {}
        cf_country = raw_headers.get("cf-ipcountry")

        # Dev fallback — mirrors GeoDetectionMiddleware behaviour.
        if not cf_country:
            cf_country = getattr(settings, "DEV_GEO_COUNTRY", None)

        # Fail-closed: unknown → 'XX' (Variant A / restricted).
        country = (cf_country or "XX").strip().upper()

        # super().onOpen() calls init_session() which resets server_data = {}.
        # Set geo_country AFTER so it isn't wiped.
        super().onOpen()

        self.server_data["geo_country"] = country

        from evennia.utils import logger
        logger.log_info(
            f"[GEO] onOpen: country={country!r} sessid={self.sessid} "
            f"server_connected={self.server_connected} "
            f"server_data={self.server_data}"
        )

        # Re-sync the portal session to the server so it receives the updated
        # server_data (sends a PCONNSYNC AMP message).
        self.sessionhandler.sync(self)

        logger.log_info(
            f"[GEO] after sync: server_connected={self.server_connected}"
        )
