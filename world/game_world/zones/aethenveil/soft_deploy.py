"""
Aethenveil Zone — soft deploy script.

Cartography tier: MASTER
Access: Overland from Bayou / Kashoryu (NE gate)

Scaffold: 3 rooms (2 gateways + 1 normal room).

Gateway keys:
    "ne_gate"  — toward Bayou / Kashoryu (MASTER cartography)
    "w_gate"   — toward Shadowsward / Scalded Waste (MASTER cartography)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "aethenveil"
DISTRICT = "aethenveil_travel"


def clean_zone():
    """Remove all Aethenveil zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Aethenveil travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING AETHENVEIL ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateway ───────────────────────────────────────────────────────

    rooms["ne_gate"] = create_object(
        RoomGateway,
        key="Forest Boundary",
        attributes=[
            ("desc",
             "The ancient forest thins at its northeastern edge, silver-"
             "barked trees giving way to open land. Elven waymarkers — "
             "slender stones carved with flowing script — line the trail. "
             "Beyond the boundary, the world feels younger and louder."),
        ],
    )

    rooms["w_gate"] = create_object(
        RoomGateway,
        key="Western Passage",
        attributes=[
            ("desc",
             "The silver forest grows sparse here, ancient trees thinning "
             "to reveal a westward trail. The air loses its timeless "
             "stillness, replaced by the dry scent of distant plains and "
             "scorched earth. Few elven waymarkers remain this far out."),
        ],
    )

    # ── Placeholder room ──────────────────────────────────────────────

    rooms["silver_glade"] = create_object(
        RoomBase,
        key="Silver Glade",
        attributes=[
            ("desc",
             "A hushed glade of silver-barked trees stretches in every "
             "direction. Shafts of pale light filter through leaves that "
             "shimmer like coins in the breeze. The air carries an "
             "ageless stillness — this forest has stood for millennia."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect_bidirectional_exit(rooms["ne_gate"], rooms["silver_glade"], "southwest")
    connect_bidirectional_exit(rooms["silver_glade"], rooms["w_gate"], "west")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.FOREST.value)

    print("  Aethenveil scaffold complete (3 rooms).\n")

    return {
        "ne_gate": rooms["ne_gate"],
        "w_gate": rooms["w_gate"],
    }


def soft_deploy():
    """Wipe and rebuild Aethenveil zone."""
    clean_zone()
    build_zone()
