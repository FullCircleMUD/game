"""
Zharavan Zone — soft deploy script.

Cartography tier: GRANDMASTER
Access: Overland from Scalded Waste (NE gate)

Scaffold: 2 rooms (1 gateway + 1 normal room).

Gateway keys:
    "ne_gate"  — toward Scalded Waste (GRANDMASTER)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "zharavan"
DISTRICT = "zharavan_travel"


def clean_zone():
    """Remove all Zharavan zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Zharavan travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING ZHARAVAN ZONE (scaffold) ===\n")

    rooms = {}

    rooms["ne_gate"] = create_object(
        RoomGateway,
        key="Hidden Gate",
        attributes=[
            ("desc",
             "A narrow pass emerges from between sheer cliff faces into "
             "an impossible valley. Lush gardens and gleaming spires "
             "stretch before you — a hidden city untouched by the ages. "
             "The desert behind seems a world away."),
        ],
    )

    rooms["outer_gardens"] = create_object(
        RoomBase,
        key="Outer Gardens",
        attributes=[
            ("desc",
             "Immaculate gardens surround you, tended by silent figures "
             "in flowing white robes. Fountains of crystal-clear water "
             "feed channels that wind between flowering trees. The city "
             "rises ahead in tiers of ivory and jade."),
        ],
    )

    connect_bidirectional_exit(rooms["ne_gate"], rooms["outer_gardens"], "southwest")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.URBAN.value)

    print("  Zharavan scaffold complete (2 rooms).\n")
    return {"ne_gate": rooms["ne_gate"]}


def soft_deploy():
    """Wipe and rebuild Zharavan zone."""
    clean_zone()
    build_zone()
