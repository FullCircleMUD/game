"""
The Arcane Sanctum Zone — soft deploy script.

Cartography tier: EXPERT
Access: Sea — Seamanship EXPERT + Brigantine

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "arcane_sanctum"


def clean_zone():
    """Remove all The Arcane Sanctum zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build The Arcane Sanctum zone. Not yet implemented."""
    print(f"  [TODO] Zone 'arcane_sanctum' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild The Arcane Sanctum zone."""
    clean_zone()
    build_zone()
