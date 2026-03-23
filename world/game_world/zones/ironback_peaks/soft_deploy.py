"""
Ironback Peaks Zone — soft deploy script.

Cartography tier: BASIC
Access: Overland from Millholm

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "ironback_peaks"


def clean_zone():
    """Remove all Ironback Peaks zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Ironback Peaks zone. Not yet implemented."""
    print(f"  [TODO] Zone 'ironback_peaks' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Ironback Peaks zone."""
    clean_zone()
    build_zone()
