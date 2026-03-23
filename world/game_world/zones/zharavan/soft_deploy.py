"""
Zharavan Zone — soft deploy script.

Cartography tier: MASTER
Access: Overland via Shadowroot or Scalded Waste

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "zharavan"


def clean_zone():
    """Remove all Zharavan zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Zharavan zone. Not yet implemented."""
    print(f"  [TODO] Zone 'zharavan' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Zharavan zone."""
    clean_zone()
    build_zone()
