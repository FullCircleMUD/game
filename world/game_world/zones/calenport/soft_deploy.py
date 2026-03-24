"""
Calenport Zone — soft deploy script.

Cartography tier: SKILLED (sea)
Access: Sea — Seamanship SKILLED + Caravel from Saltspray Bay / Kashoryu

Scaffold: 2 rooms (1 dock gateway + 1 normal room).

Gateway keys:
    "dock"  — sea routes back to Saltspray Bay / Kashoryu
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "calenport"
DISTRICT = "calenport_travel"


def clean_zone():
    """Remove all Calenport zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Calenport travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING CALENPORT ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Calenport Pier",
        attributes=[
            ("desc",
             "A long wooden pier stretches into a natural harbour "
             "sheltered by rocky headlands. Pirate flags fly openly "
             "from half the vessels moored here. The town sprawls "
             "along the waterfront — a lawless, colourful jumble of "
             "taverns, fighting pits, and black-market stalls."),
        ],
    )

    rooms["pirate_quarter"] = create_object(
        RoomBase,
        key="Pirate Quarter",
        attributes=[
            ("desc",
             "The main street of Calenport reeks of rum and gunpowder. "
             "Every other building is a tavern, and the rest are worse. "
             "Wanted posters paper the walls — most of them bearing the "
             "faces of people drinking in plain sight nearby."),
        ],
    )

    connect(rooms["dock"], rooms["pirate_quarter"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["dock"].set_terrain(TerrainType.COASTAL.value)
    rooms["pirate_quarter"].set_terrain(TerrainType.URBAN.value)

    print("  Calenport scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild Calenport zone."""
    clean_zone()
    build_zone()
