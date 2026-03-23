"""
The Bayou Zone — soft deploy script.

Cartography tier: SKILLED
Access: Overland via Ironback Peaks or Cloverfen

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "bayou"


def clean_zone():
    """Remove all The Bayou zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build The Bayou zone. Not yet implemented."""
    print(f"  [TODO] Zone 'bayou' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild The Bayou zone."""
    clean_zone()
    build_zone()
