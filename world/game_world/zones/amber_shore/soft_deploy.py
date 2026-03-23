"""
Amber Shore Zone — soft deploy script.

Cartography tier: SKILLED
Access: Sea — Seamanship SKILLED + Caravel

Not yet implemented.
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "amber_shore"


def clean_zone():
    """Remove all Amber Shore zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Amber Shore zone. Not yet implemented."""
    print(f"  [TODO] Zone 'amber_shore' is not yet built — skipping.")
    return {}


def soft_deploy():
    """Wipe and rebuild Amber Shore zone."""
    clean_zone()
    build_zone()
