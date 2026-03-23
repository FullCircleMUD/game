"""
Scalded Waste Zone — soft deploy script.

Cartography tier: EXPERT
Access: Overland via Saltspray Bay or The Bayou

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "scalded_waste"


def clean_zone():
    """Remove all Scalded Waste zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Scalded Waste zone. Not yet implemented."""
    print(f"  [TODO] Zone 'scalded_waste' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Scalded Waste zone."""
    clean_zone()
    build_zone()
