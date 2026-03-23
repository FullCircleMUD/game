"""
Kashoryu Zone — soft deploy script.

Cartography tier: SKILLED/EXPERT
Access: Sea SKILLED + Caravel; overland EXPERT via Bayou; overland MASTER via Aethenveil

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "kashoryu"


def clean_zone():
    """Remove all Kashoryu zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Kashoryu zone. Not yet implemented."""
    print(f"  [TODO] Zone 'kashoryu' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Kashoryu zone."""
    clean_zone()
    build_zone()
