"""
Calenport Zone — soft deploy script.

Cartography tier: BASIC
Access: Sea — Seamanship BASIC + Cog

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "calenport"


def clean_zone():
    """Remove all Calenport zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Calenport zone. Not yet implemented."""
    print(f"  [TODO] Zone 'calenport' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Calenport zone."""
    clean_zone()
    build_zone()
