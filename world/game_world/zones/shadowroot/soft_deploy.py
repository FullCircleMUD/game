"""
Shadowroot Zone — soft deploy script.

Cartography tier: EXPERT
Access: Overland via Saltspray Bay or The Bayou

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "shadowroot"


def clean_zone():
    """Remove all Shadowroot zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Shadowroot zone. Not yet implemented."""
    print(f"  [TODO] Zone 'shadowroot' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Shadowroot zone."""
    clean_zone()
    build_zone()
