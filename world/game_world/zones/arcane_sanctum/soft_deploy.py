"""
The Arcane Sanctum Zone — soft deploy script.

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
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "arcane_sanctum"
DISTRICT = "arcane_sanctum_travel"


def clean_zone():
    """Remove all The Arcane Sanctum zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build The Arcane Sanctum travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING THE ARCANE SANCTUM ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Sanctum Moorings",
        attributes=[
            ("desc",
             "A single stone quay emerges from swirling mist. The island "
             "beyond is barely visible — towers and spires materialise "
             "and vanish in the fog as though the place can't quite "
             "decide whether to exist. Arcane wards hum faintly in the "
             "stonework beneath your feet."),
        ],
    )

    rooms["mist_path"] = create_object(
        RoomBase,
        key="Mist-Shrouded Path",
        attributes=[
            ("desc",
             "A narrow path of perfectly smooth stone leads inland "
             "through impossibly thick mist. Glowing runes pulse along "
             "the edges, the only guide in the white void. Somewhere "
             "ahead, the soft chime of crystal bells promises the "
             "Sanctum proper."),
        ],
    )

    connect(rooms["dock"], rooms["mist_path"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["dock"].set_terrain(TerrainType.COASTAL.value)
    rooms["mist_path"].set_terrain(TerrainType.FOREST.value)

    print("  The Arcane Sanctum scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild The Arcane Sanctum zone."""
    clean_zone()
    build_zone()
