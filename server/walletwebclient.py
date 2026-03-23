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

SESSION SECURITY
---------------
Evennia's default disconnect() uses a nonce to guard the Django session
webclient_authenticated_uid field.  The nonce is stored in the Django
session and incremented by SharedLoginMiddleware on every HTTP request.
By the time the user quits, the session nonce has drifted far above the
value captured at WebSocket open time, so the nonce check always fails
and webclient_authenticated_uid is never cleared — a hard browser refresh
after logout re-authenticates the player without any credential challenge.

We fix this by overriding disconnect() with a stable per-connection token
(self._ws_token) written to the Django session at open time.  Token match
on disconnect → clear uid.  A later connection writing a new token means
the old connection's disconnect can no longer clear the uid (preserves the
multi-tab race-condition protection the nonce was meant to provide).
"""

import uuid

from django.conf import settings
from evennia.server.portal.webclient import CLOSE_NORMAL, WebSocketClient


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

        # Stamp a stable per-connection token so disconnect() can reliably
        # clear the Django session.  See module docstring for why the default
        # nonce-based check is broken in this app.
        self._ws_token = str(uuid.uuid4())
        csession = self.get_client_session()
        if csession:
            csession["ws_session_token"] = self._ws_token
            csession.save()

        # Belt-and-suspenders: re-sync in case the portal session was updated
        # after the initial PCONN (e.g. throttled connection path).
        self.sessionhandler.sync(self)

    def disconnect(self, reason=None):
        """Override to fix session cookie not being cleared on logout.

        Two compounding bugs in Evennia's default behaviour:

        1. Nonce drift: SharedLoginMiddleware increments
           webclient_authenticated_nonce on every HTTP request, so the nonce
           stored on self (captured at open time) never matches the session
           nonce at disconnect time → uid is never cleared.

        2. Django re-auth: SharedLoginMiddleware's make_shared_login() calls
           Django's login() the first time webclient_uid is set, writing
           _auth_user_id to the Django session.  On a subsequent HTTP request
           (e.g. hard browser refresh) it sees account.is_authenticated=True
           and webclient_uid=None → re-sets webclient_authenticated_uid
           automatically, reinstating the auto-login.

        Fix: on a clean disconnect (token matches), clear both the Evennia
        webclient keys AND the Django auth session keys so the middleware
        cannot re-authenticate the player.  The stable per-connection UUID
        token (vs the drifting nonce) is what makes the token match reliable.
        """
        csession = self.get_client_session()
        if csession:
            stored_token = csession.get("ws_session_token")
            our_token = getattr(self, "_ws_token", None)
            if stored_token and stored_token == our_token:
                # Clear Evennia webclient keys
                csession["webclient_authenticated_uid"] = None
                csession["webclient_authenticated_nonce"] = 0
                csession["website_authenticated_uid"] = None
                csession["ws_session_token"] = None
                # Clear Django auth session so SharedLoginMiddleware cannot
                # re-set webclient_authenticated_uid on the next HTTP request
                csession.pop("_auth_user_id", None)
                csession.pop("_auth_user_backend", None)
                csession.pop("_auth_user_hash", None)
                csession.save()
            self.logged_in = False

        self.sessionhandler.disconnect(self)
        self.sendClose(CLOSE_NORMAL, reason)
