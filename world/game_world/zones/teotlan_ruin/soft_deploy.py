"""
Teotlan Ruin Zone — soft deploy script.

Cartography tier: BASIC (sea)
Access: Sea — Seamanship BASIC + Cog from Saltspray Bay / Kashoryu

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

ZONE_KEY = "teotlan_ruin"
DISTRICT = "teotlan_ruin_travel"


def clean_zone():
    """Remove all Teotlan Ruin zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Teotlan Ruin travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING TEOTLAN RUIN ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Teotlan Landing",
        attributes=[
            ("desc",
             "A crumbling stone jetty juts into a sheltered cove. "
             "Jungle vines have reclaimed much of the ancient masonry. "
             "Carved serpent heads stare from moss-covered pillars, "
             "their eyes worn smooth by centuries of rain."),
        ],
    )

    rooms["temple_approach"] = create_object(
        RoomBase,
        key="Temple Approach",
        attributes=[
            ("desc",
             "A stone-paved road climbs from the landing into dense "
             "tropical jungle. Enormous stepped pyramids rise above the "
             "canopy ahead, their peaks catching the sun. The air thrums "
             "with the sound of insects and distant drumming."),
        ],
    )

    connect_bidirectional_exit(rooms["dock"], rooms["temple_approach"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["dock"].set_terrain(TerrainType.COASTAL.value)
    rooms["temple_approach"].set_terrain(TerrainType.FOREST.value)

    print("  Teotlan Ruin scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild Teotlan Ruin zone."""
    clean_zone()
    build_zone()
