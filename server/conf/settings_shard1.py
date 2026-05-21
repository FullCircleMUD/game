"""
Shard1 settings for FCM.

Usage:
    evennia start --settings settings_shard1.py

Second shard, used during pre-alpha as a spike to prove the cross-shard
handoff machinery works end-to-end before production. Shipped behind
the scenes so adding a second shard later (when load demands it) is a
config flip, not a new feature. See design/SCALING.md for the
multi-shard intent and design/WORLD_DEPLOYMENT.md for how zones map to
shards.

Cascade:
    settings_shard1.py (this file)
        -> settings_common_shard_config.py
            -> settings.py
"""

from server.conf.settings_common_shard_config import *  # noqa: F401, F403

from evennia_shards import ROLE_SHARD

SHARDS_ROLE = ROLE_SHARD
SHARD_ID = "shard1"

# Shards MUST auto-puppet: the ticket-based auth flow logs the player
# in, then Evennia's at_post_login reads _last_puppet (which the
# router set during ticket creation) to puppet the chosen character.
# This is the library's required behaviour on the shard side, and
# overrides FCM's monolith-mode AUTO_PUPPET_ON_LOGIN=False from
# settings.py.
AUTO_PUPPET_ON_LOGIN = True

# Per-shard DEFAULT_HOME. Evennia's create_object falls back to
# settings.DEFAULT_HOME when no explicit home= kwarg is passed, and
# it resolves the dbref by loading the row. A cross-shard pointer
# (e.g. shard0's Limbo #2 from a shard1 process) trips the library's
# from_db chokepoint — so each shard must point DEFAULT_HOME at a
# room it actually owns.
#
# Shard1's "Limbo equivalent" is the cross-shard-dug Shard1-Limbo
# room (created via library's `cross_shard_dig` command and stamped
# shard_id="shard1"). This pk needs to stay stable for the deployment;
# update if the bootstrap topology changes.
#
# START_LOCATION stays at #2 (shard0's Limbo) because chargen runs
# router-side and the library's chargen wrapper stamps the new
# character with the start-location's shard_id — so new characters
# spawn on shard0 (the populated world), not here.
DEFAULT_HOME = "#4"
START_LOCATION = "#2"

# Localhost ports — offset by 20 from the router so a developer can
# run router + shard0 + shard1 simultaneously without collisions. On
# Railway each service binds the platform's $PORT and these are not
# used.
WEBSERVER_PORTS = [(4021, 4025)]
WEBSOCKET_CLIENT_PORT = 4022
AMP_PORT = 4026

# Shards never serve the webclient page, the website, or static
# assets — those live on the router. evennia_shards.portal_services
# registers the webclient WebSocket independently when this is
# False, so disabling the HTTP stack drops only the parts the shard
# doesn't need (reverse-proxy, Django views, WEB_PLUGINS_MODULE,
# AJAX webclient fallback).
WEBSERVER_ENABLED = False
