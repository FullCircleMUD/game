"""
The Shadowsward Zone — soft deploy script.

Cartography tier: SKILLED
Access: Overland via Ironback Peaks or Cloverfen

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "shadowsward"


def clean_zone():
    """Remove all The Shadowsward zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build The Shadowsward zone. Not yet implemented."""
    print(f"  [TODO] Zone 'shadowsward' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild The Shadowsward zone."""
    clean_zone()
    build_zone()
