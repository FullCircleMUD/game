"""
Amber Shore Zone — soft deploy script.

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
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "amber_shore"
DISTRICT = "amber_shore_travel"


def clean_zone():
    """Remove all Amber Shore zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Amber Shore travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING AMBER SHORE ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Amber Shore Landing",
        attributes=[
            ("desc",
             "A makeshift wooden dock extends into murky shallows. The "
             "beach is a sickly amber colour, and the air hangs thick "
             "with the smell of rot and medicinal herbs. A quarantine "
             "flag flutters from a crooked pole."),
        ],
    )

    rooms["colonial_road"] = create_object(
        RoomBase,
        key="Colonial Road",
        attributes=[
            ("desc",
             "A rutted dirt road leads inland from the dock through "
             "scrubby vegetation. Abandoned colonial buildings line the "
             "way, their shutters nailed closed. Somewhere ahead, smoke "
             "rises from the settlement that persists despite the plague."),
        ],
    )

    connect_bidirectional_exit(rooms["dock"], rooms["colonial_road"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["dock"].set_terrain(TerrainType.COASTAL.value)
    rooms["colonial_road"].set_terrain(TerrainType.PLAINS.value)

    print("  Amber Shore scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild Amber Shore zone."""
    clean_zone()
    build_zone()
