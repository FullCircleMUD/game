"""
Solendra Zone — soft deploy script.

Cartography tier: GRANDMASTER (sea)
Access: Sea — Seamanship GRANDMASTER + Galleon from Kashoryu

Scaffold: 2 rooms (1 dock gateway + 1 normal room).

Gateway keys:
    "dock"  — sea routes back to Kashoryu
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "solendra"
DISTRICT = "solendra_travel"


def clean_zone():
    """Remove all Solendra zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Solendra travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING SOLENDRA ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Solendra Harbour",
        attributes=[
            ("desc",
             "A vast harbour carved from living coral stretches before you. "
             "Ships of unfamiliar design bob at anchor, their sails shimmering "
             "with iridescent thread. The city beyond rises in tiers of white "
             "stone and blue-tiled domes, utterly unlike anything in the "
             "known world."),
        ],
    )

    rooms["harbour_plaza"] = create_object(
        RoomBase,
        key="Harbour Plaza",
        attributes=[
            ("desc",
             "A broad plaza of polished stone opens beyond the harbour. "
             "Merchants in flowing robes trade in languages you have never "
             "heard. Strange spices scent the air, and the architecture "
             "speaks of a civilisation old beyond reckoning."),
        ],
    )

    connect(rooms["dock"], rooms["harbour_plaza"], "north")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["dock"].set_terrain(TerrainType.COASTAL.value)
    rooms["harbour_plaza"].set_terrain(TerrainType.URBAN.value)

    print("  Solendra scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild Solendra zone."""
    clean_zone()
    build_zone()
