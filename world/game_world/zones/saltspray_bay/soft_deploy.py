"""
Saltspray Bay Zone — soft deploy script.

Cartography tier: SKILLED
Access: Overland via Ironback Peaks or Cloverfen

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "saltspray_bay"


def clean_zone():
    """Remove all Saltspray Bay zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Saltspray Bay zone. Not yet implemented."""
    print(f"  [TODO] Zone 'saltspray_bay' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Saltspray Bay zone."""
    clean_zone()
    build_zone()
