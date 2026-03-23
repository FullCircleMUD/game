"""
Teotlan Ruin Zone — soft deploy script.

Cartography tier: BASIC
Access: Sea — Seamanship BASIC + Cog

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "teotlan_ruin"


def clean_zone():
    """Remove all Teotlan Ruin zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Teotlan Ruin zone. Not yet implemented."""
    print(f"  [TODO] Zone 'teotlan_ruin' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Teotlan Ruin zone."""
    clean_zone()
    build_zone()
