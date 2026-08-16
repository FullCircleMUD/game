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
# In production this is set via the SHARDS_ROUTER_URL env var on every
# Railway service.
ROUTER_URL = os.environ.get(
    "SHARDS_ROUTER_URL",
    "ws://localhost:4002/",
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
# In production, override the per-shard URL via SHARDS_SHARD0_URL,
# SHARDS_SHARD1_URL, ... env vars.
SHARD_URLS = {
    "shard0": os.environ.get(
        "SHARDS_SHARD0_URL",
        "ws://localhost:4012/",
    ),
    "shard1": os.environ.get(
        "SHARDS_SHARD1_URL",
        "ws://localhost:4022/",
    ),
}

# Telnet has no mechanism to carry a ticket token (no URL, no query
# params), so the library's WebSocket-only ticket auth flow doesn't
# extend to it. FCM's base settings.py already disables telnet (see
# docs/connection-transport.md), but make it explicit here so the
# requirement is visible to anyone reading just the shard cascade.
TELNET_ENABLED = False

# Tickets don't record the address they were issued to, because on Railway
# no process can observe it. Traffic reaches a container through Railway's
# proxy, so a shard sees a private 100.64.0.0/10 address rather than the
# player's — never the one the router recorded, so every redirect was
# refused with "Ticket rejected: IP mismatch".
#
# The library resolves the real address from x-forwarded-for, but only when
# the immediate peer is listed in Evennia's UPSTREAM_IPS, which is an
# exact-match list and so can't express a proxy drawn from a range.
#
# What this costs: tickets stay single-use and short-lived, so the loss is
# only protection against replay from a second address — which was never
# available here anyway.
#
# Deployment-wide rather than per-role: the router records the address and
# the shard checks it, so the two must agree. One line in the shared file
# makes disagreement impossible.
SHARDS_TICKET_BIND_IP = False
