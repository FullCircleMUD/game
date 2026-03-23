"""
Atlantis Zone — soft deploy script.

Cartography tier: MASTER
Access: Overland (dive) — swim off Guildmere Island beach, dive through underwater cave. Water Breathing required.

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "atlantis"


def clean_zone():
    """Remove all Atlantis zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Atlantis zone. Not yet implemented."""
    print(f"  [TODO] Zone 'atlantis' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Atlantis zone."""
    clean_zone()
    build_zone()
