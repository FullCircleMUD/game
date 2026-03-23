"""
Port Shadowmere Zone — soft deploy script.

Cartography tier: SKILLED
Access: Sea — Seamanship SKILLED + Caravel

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "port_shadowmere"


def clean_zone():
    """Remove all Port Shadowmere zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Port Shadowmere zone. Not yet implemented."""
    print(f"  [TODO] Zone 'port_shadowmere' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Port Shadowmere zone."""
    clean_zone()
    build_zone()
