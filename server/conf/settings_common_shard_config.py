"""
Common shard configuration shared by all sharded FCM instances (router,
shard0, shard1, ...).

Cascade:
    settings_router.py / settings_shard0.py
        -> settings_common_shard_config.py (this file)
            -> settings.py (base FCM config; loads secret_settings.local)

Settings that are deployment-wide (URL maps, INSTALLED_APPS additions,
the global TELNET disable) live here. Settings that differ per role
(SHARDS_ROLE, SHARD_ID, ports, AUTO_PUPPET_ON_LOGIN, DEFAULT_HOME) live
in settings_router.py / settings_shard0.py.

Base settings.py is the monolith-mode config and remains usable on its
own — running `evennia start` from src/game/ without --settings still
launches FCM as a single process with the shards library dormant.
"""

import os

from server.conf.settings import *  # noqa: F401, F403 — base FCM config

# evennia_shards is only added to INSTALLED_APPS when we're running in a
# sharded role. Monolith deployments (the default) don't include it, so
# the library stays genuinely dormant — no AppConfig.ready() side-effects,
# no migration runs, no chokepoint installation.
INSTALLED_APPS = list(INSTALLED_APPS) + ["evennia_shards"]  # type: ignore[name-defined]

# WebSocket URL of the router process. Shards use this to redirect a
# player back to the router on `@ooc`. WebSocket-level redirect: JS in
# the webclient closes its current WS and opens a new one to this URL
# with ?ticket=TOKEN appended. The page itself is NOT reloaded.
#
# Derived from FCM_HOSTNAME (read in settings.py from /etc/fcm/env).
# One hostname serves every role; nginx demuxes by path — /ws/ to the
# router on 4002, /ws/shard0/ to 4012, /ws/shard1/ to 4022.
ROUTER_URL = os.environ.get(
    "SHARDS_ROUTER_URL",
    f"wss://{FCM_HOSTNAME}/ws/" if FCM_HOSTNAME else "ws://localhost:4002/",  # noqa: F405
)

# Map of shard_id -> WebSocket URL. Router uses this to redirect a
# player IC to whichever shard owns their character's location/home
# room. Same WebSocket-level redirect shape as ROUTER_URL above.
#
# Shard IDs are flexible — name them to match the game world. FCM
# starts with a single "shard0" because we deploy the architecture
# with shard_count=1 first (see docs/scaling.md for the design
# rationale).
#
# Derived from FCM_HOSTNAME like ROUTER_URL above. Override an individual
# shard with SHARDS_SHARD0_URL, SHARDS_SHARD1_URL, ... if one ever needs to
# live somewhere else.
#
# Keep the trailing slash. The redirect URL is built by concatenation
# (`f"{url}?ticket={token}"`), so without it the path is /ws/shard0, which
# misses nginx's `location /ws/shard0/`, falls through to `location /ws/`,
# and lands the player on the router instead of the shard.
SHARD_URLS = {
    "shard0": os.environ.get(
        "SHARDS_SHARD0_URL",
        f"wss://{FCM_HOSTNAME}/ws/shard0/" if FCM_HOSTNAME else "ws://localhost:4012/",  # noqa: F405
    ),
    "shard1": os.environ.get(
        "SHARDS_SHARD1_URL",
        f"wss://{FCM_HOSTNAME}/ws/shard1/" if FCM_HOSTNAME else "ws://localhost:4022/",  # noqa: F405
    ),
}

# Telnet has no mechanism to carry a ticket token (no URL, no query
# params), so the library's WebSocket-only ticket auth flow doesn't
# extend to it. FCM's base settings.py already disables telnet (see
# docs/connection-transport.md), but make it explicit here so the
# requirement is visible to anyone reading just the shard cascade.
TELNET_ENABLED = False

# A ticket records the address it was issued to, and the receiving shard
# refuses a connection from any other — so a stolen token is useless from
# a second machine.
#
# This needs the player's real address on both sides. Evennia reads it from
# x-forwarded-for, but only when the immediate peer is listed in
# UPSTREAM_IPS (an exact-match list). Behind nginx the peer is 127.0.0.1,
# which UPSTREAM_IPS lists by default, and the Cloudflare real-IP snippet
# gives nginx the player's address to forward. Both conditions hold.
#
# The check is exact-match, so a player whose address changes between going
# IC and the shard connecting is refused with "Ticket rejected: IP
# mismatch". Mobile networks do that.
#
# Deployment-wide rather than per-role: the router records the address and
# the shard checks it, so the two must agree. One line in the shared file
# makes disagreement impossible.
SHARDS_TICKET_BIND_IP = True
