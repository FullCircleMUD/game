"""
Vaathari Zone — soft deploy script.

Cartography tier: GRANDMASTER
Access: Sea — Seamanship GRANDMASTER + Galleon from Guildmere Island

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "vaathari"


def clean_zone():
    """Remove all Vaathari zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Vaathari zone. Not yet implemented."""
    print(f"  [TODO] Zone 'vaathari' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Vaathari zone."""
    clean_zone()
    build_zone()
