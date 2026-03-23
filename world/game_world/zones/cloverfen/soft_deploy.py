"""
Cloverfen Zone — soft deploy script.

Cartography tier: BASIC
Access: Overland from Millholm

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "cloverfen"


def clean_zone():
    """Remove all Cloverfen zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Cloverfen zone. Not yet implemented."""
    print(f"  [TODO] Zone 'cloverfen' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Cloverfen zone."""
    clean_zone()
    build_zone()
