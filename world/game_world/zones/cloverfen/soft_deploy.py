"""
Cloverfen Zone — soft deploy script.

Cartography tier: BASIC
Access: Overland from Millholm (NW gate), overland to Saltspray Bay (E gate)

Scaffold: 3 rooms (2 gateways + 1 connecting room).

Gateway keys:
    "nw_gate"  — toward Millholm / Ironback Peaks (BASIC cartography)
    "e_gate"   — toward Saltspray Bay (SKILLED cartography)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "cloverfen"
DISTRICT = "cloverfen_travel"


def clean_zone():
    """Remove all Cloverfen zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Cloverfen travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING CLOVERFEN ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateways ──────────────────────────────────────────────────────

    rooms["nw_gate"] = create_object(
        RoomGateway,
        key="Cloverfen Crossroads",
        attributes=[
            ("desc",
             "A well-trodden crossroads at the edge of halfling country. "
             "Gentle hills roll away in every direction, dotted with "
             "hedgerows and wildflowers. A wooden signpost points toward "
             "distant mountains and the familiar farmlands of home."),
        ],
    )

    rooms["e_gate"] = create_object(
        RoomGateway,
        key="Eastern Trade Road",
        attributes=[
            ("desc",
             "The trade road stretches eastward across open plains, "
             "gradually descending toward the salt-tinged air of the "
             "coast. Merchant carts have worn deep ruts in the packed "
             "earth."),
        ],
    )

    # ── Connecting room ───────────────────────────────────────────────

    rooms["halfling_green"] = create_object(
        RoomBase,
        key="Halfling Green",
        attributes=[
            ("desc",
             "A broad village green surrounded by low stone walls and "
             "neat hedgerows. Round doors peek from hillsides on every "
             "side. The air smells of pipe-weed and fresh bread. A "
             "signpost in the centre points in all directions."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect(rooms["nw_gate"], rooms["halfling_green"], "southeast")
    connect(rooms["halfling_green"], rooms["e_gate"], "east")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.PLAINS.value)

    print("  Cloverfen scaffold complete (3 rooms).\n")

    return {
        "nw_gate": rooms["nw_gate"],
        "e_gate": rooms["e_gate"],
    }


def soft_deploy():
    """Wipe and rebuild Cloverfen zone."""
    clean_zone()
    build_zone()
