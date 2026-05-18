"""
Router-mode settings for FCM.

Usage:
    evennia start --settings settings_router.py

The router process owns AccountDB (login, characters list, account
bank) and runs the website + webclient page + Django admin. It does
NOT own game-world rooms or characters — those live on shards. On
`@ic` the router resolves the chosen character, mints a single-use
ticket, and redirects the player's WebSocket to the shard that owns
the character's location/home room.

Cascade:
    settings_router.py (this file)
        -> settings_common_shard_config.py
            -> settings.py
"""

from server.conf.settings_common_shard_config import *  # noqa: F401, F403

from evennia_shards import ROLE_ROUTER, get_router_shard_id

SHARDS_ROLE = ROLE_ROUTER

# Library mandate: the router's SHARD_ID equals get_router_shard_id()
# (the constant "router"). Derive from the accessor rather than the
# literal so any future rename in evennia_shards propagates here for
# free.
SHARD_ID = get_router_shard_id()

# Manual character selection at the OOC menu — the player types
# `ic <character>` after login. The router's at_post_login override
# intercepts this and redirects to the correct shard via ticket.
#
# Inherits from settings.py (FCM sets this to False already), but
# stated explicitly here so the router behaviour is self-documenting.
AUTO_PUPPET_ON_LOGIN = False

# Localhost ports. On Railway these are overridden by the platform's
# $PORT env var (already handled in base settings.py).
WEBSERVER_PORTS = [(4001, 4005)]
WEBSOCKET_CLIENT_PORT = 4002
AMP_PORT = 4006

# The router serves the webclient page, the website (fcmud.world),
# the static-asset pipeline, and the Django admin. Shards run
# WebSocket-only — see settings_shard0.py.
WEBSERVER_ENABLED = True
