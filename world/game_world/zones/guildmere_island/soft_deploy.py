"""
Guildmere Island Zone — soft deploy script.

Cartography tier: MASTER
Access: Sea — Seamanship MASTER + Carrack

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "guildmere_island"


def clean_zone():
    """Remove all Guildmere Island zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Guildmere Island zone. Not yet implemented."""
    print(f"  [TODO] Zone 'guildmere_island' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Guildmere Island zone."""
    clean_zone()
    build_zone()
