"""
Oldbone Island Zone — soft deploy script.

Cartography tier: EXPERT
Access: Sea — Seamanship EXPERT + Brigantine

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "oldbone_island"


def clean_zone():
    """Remove all Oldbone Island zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Oldbone Island zone. Not yet implemented."""
    print(f"  [TODO] Zone 'oldbone_island' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Oldbone Island zone."""
    clean_zone()
    build_zone()
