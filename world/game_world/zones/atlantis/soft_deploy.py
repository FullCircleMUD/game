"""
Atlantis Zone — soft deploy script.

Cartography tier: MASTER (overland/dive)
Access: Dive from Guildmere Island Coral Beach. Water Breathing required.

Scaffold: 2 rooms (1 gateway + 1 normal room). Temporary endpoint.

Gateway keys:
    "s_gate"  — dive route back to Guildmere Island
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "atlantis"
DISTRICT = "atlantis_travel"


def clean_zone():
    """Remove all Atlantis zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Atlantis travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING ATLANTIS ZONE (scaffold) ===\n")

    rooms = {}

    rooms["s_gate"] = create_object(
        RoomGateway,
        key="Underwater Cavern Mouth",
        attributes=[
            ("desc",
             "A vast underwater cavern opens before you, its walls "
             "encrusted with luminous coral and pearl. Warm currents "
             "flow outward from the depths, carrying the faint sound "
             "of distant music. Above, the surface glimmers far "
             "overhead — the dive from Guildmere's coral beach."),
        ],
    )

    rooms["coral_passage"] = create_object(
        RoomBase,
        key="Coral Passage",
        attributes=[
            ("desc",
             "A breathtaking passage of living coral stretches into "
             "the deep. Bioluminescent creatures drift past, casting "
             "shifting light across walls carved with ancient symbols. "
             "The water grows warmer as the passage descends toward "
             "something vast and luminous below."),
        ],
    )

    connect(rooms["s_gate"], rooms["coral_passage"], "north")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.WATER.value)

    print("  Atlantis scaffold complete (2 rooms).\n")
    return {"s_gate": rooms["s_gate"]}


def soft_deploy():
    """Wipe and rebuild Atlantis zone."""
    clean_zone()
    build_zone()
