"""
Custom WebSocket handler.

Extends Evennia's default WebSocketClient to capture the Cloudflare
CF-IPCountry header and deliver it to the server session via the initial
PCONN AMP message.

The geo country is injected in get_sync_data() so it is present in the
PCONN packet that portalsessionhandler.connect() sends to the server.
This ensures at_post_login() sees the correct country even for auto-login
sessions (returning browser cookies), where at_post_login fires during PCONN
processing before any PCONNSYNC could arrive.

In production, Cloudflare injects CF-IPCountry on every WebSocket upgrade
request when the DNS proxy is enabled.  In development, falls back to the
DEV_GEO_COUNTRY Django setting (mirrors the geo middleware behaviour).
"""

from django.conf import settings
from evennia.server.portal.webclient import WebSocketClient


class WalletWebSocketClient(WebSocketClient):
    """Custom WebSocket client — delivers geo-country in the initial PCONN."""

    def get_sync_data(self):
        """Override to inject geo_country into the initial PCONN message.

        portalsessionhandler.connect() calls this to build the session data
        that gets sent with PCONN.  By injecting geo_country here it arrives
        at the server in the initial packet — before at_post_login() fires
        for auto-login sessions.
        """
        data = super().get_sync_data()

        raw_headers = getattr(self, "http_headers", {}) or {}
        cf_country = raw_headers.get("cf-ipcountry")
        if not cf_country:
            cf_country = getattr(settings, "DEV_GEO_COUNTRY", None)
        country = (cf_country or "XX").strip().upper()

        server_data = dict(data.get("server_data") or {})
        server_data["geo_country"] = country
        data["server_data"] = server_data
        return data

    def onOpen(self):
        super().onOpen()

        # Mirror geo_country on the local portal session for consistency.
        # The critical delivery path is get_sync_data() above.
        raw_headers = getattr(self, "http_headers", {}) or {}
        cf_country = raw_headers.get("cf-ipcountry")
        if not cf_country:
            cf_country = getattr(settings, "DEV_GEO_COUNTRY", None)
        self.server_data["geo_country"] = (cf_country or "XX").strip().upper()

        # Belt-and-suspenders: re-sync in case the portal session was updated
        # after the initial PCONN (e.g. throttled connection path).
        self.sessionhandler.sync(self)
