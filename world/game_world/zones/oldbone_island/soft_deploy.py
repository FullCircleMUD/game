"""
Oldbone Island Zone — soft deploy script.

Cartography tier: EXPERT (sea)
Access: Sea — Seamanship EXPERT + Brigantine from Saltspray Bay / Kashoryu

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

ZONE_KEY = "oldbone_island"
DISTRICT = "oldbone_island_travel"


def clean_zone():
    """Remove all Oldbone Island zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Oldbone Island travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING OLDBONE ISLAND ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Oldbone Anchorage",
        attributes=[
            ("desc",
             "A weathered dock built from the bones of some enormous "
             "creature juts into a warm lagoon. The beach is littered "
             "with fossils the size of boulders. Dense jungle crowds "
             "the shore, and something very large moves in the canopy "
             "beyond."),
        ],
    )

    rooms["fossil_beach"] = create_object(
        RoomBase,
        key="Fossil Beach",
        attributes=[
            ("desc",
             "Enormous bones protrude from the sand — ribs taller than "
             "a man, skulls with teeth like swords. The jungle behind "
             "the beach echoes with deep, rumbling calls that shake the "
             "ground. This island is home to creatures that should have "
             "been extinct for millennia."),
        ],
    )

    connect_bidirectional_exit(rooms["dock"], rooms["fossil_beach"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["dock"].set_terrain(TerrainType.COASTAL.value)
    rooms["fossil_beach"].set_terrain(TerrainType.COASTAL.value)

    print("  Oldbone Island scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild Oldbone Island zone."""
    clean_zone()
    build_zone()
