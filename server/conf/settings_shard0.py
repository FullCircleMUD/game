"""
Shard0 settings for FCM.

Usage:
    evennia start --settings settings_shard0.py

A shard process owns its slice of the game world (rooms, characters
in residence, items, NPCs, mobs). It accepts ticket-authenticated
WebSocket sessions from the router (on `@ic`) and from other shards
(on cross-shard movement). It does NOT own AccountDB rows — those
live on the router.

In the single-Postgres era FCM starts with one shard ("shard0"); the
architecture supports adding shard1, shard2, ... by config alone
(per design/SCALING.md). Until then, every game-world row is owned
by shard0.

Cascade:
    settings_shard0.py (this file)
        -> settings_common_shard_config.py
            -> settings.py
"""

from server.conf.settings_common_shard_config import *  # noqa: F401, F403

from evennia_shards import ROLE_SHARD

SHARDS_ROLE = ROLE_SHARD
SHARD_ID = "shard0"

# Shards MUST auto-puppet: the ticket-based auth flow logs the player
# in, then Evennia's at_post_login reads _last_puppet (which the
# router set during ticket creation) to puppet the chosen character.
# This is the library's required behaviour on the shard side, and
# overrides FCM's monolith-mode AUTO_PUPPET_ON_LOGIN=False from
# settings.py.
AUTO_PUPPET_ON_LOGIN = True

# Limbo (#2) is created by Evennia's initial_setup and serves as the
# fallback home/start room. The library's pre_save chokepoint auto-
# stamps it with SHARD_ID when initial_setup runs on this process.
#
# For multi-shard deployments this would be replaced with the PK of
# a shard-specific landing room. For shard_count=1 the default works.
DEFAULT_HOME = "#2"
START_LOCATION = "#2"

# Localhost ports — offset by 10 from the router so a developer can
# run both processes simultaneously. On Railway each service binds
# the platform's $PORT and these are not used.
WEBSERVER_PORTS = [(4011, 4015)]
WEBSOCKET_CLIENT_PORT = 4012
AMP_PORT = 4016

# Shards never serve the webclient page, the website, or static
# assets — those live on the router. evennia_shards.portal_services
# registers the webclient WebSocket independently when this is
# False, so disabling the HTTP stack drops only the parts the shard
# doesn't need (reverse-proxy, Django views, WEB_PLUGINS_MODULE,
# AJAX webclient fallback).
WEBSERVER_ENABLED = False
