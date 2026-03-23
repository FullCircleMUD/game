"""
Aethenveil Zone — soft deploy script.

Cartography tier: MASTER
Access: Overland via Shadowroot or Scalded Waste

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "aethenveil"


def clean_zone():
    """Remove all Aethenveil zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Aethenveil zone. Not yet implemented."""
    print(f"  [TODO] Zone 'aethenveil' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Aethenveil zone."""
    clean_zone()
    build_zone()
