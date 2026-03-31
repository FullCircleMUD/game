"""
Ironback Peaks Zone — soft deploy script.

Cartography tier: BASIC
Access: Overland from Millholm (SW gate), overland to Saltspray Bay (S gate)

Scaffold: 3 rooms (2 gateways + 1 connecting room).

Gateway keys:
    "sw_gate"  — toward Millholm / Cloverfen (BASIC cartography)
    "s_gate"   — toward Saltspray Bay (SKILLED cartography)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "ironback_peaks"
DISTRICT = "ironback_peaks_travel"


def clean_zone():
    """Remove all Ironback Peaks zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Ironback Peaks travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING IRONBACK PEAKS ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateways ──────────────────────────────────────────────────────

    rooms["sw_gate"] = create_object(
        RoomGateway,
        key="Mountain Pass",
        attributes=[
            ("desc",
             "A narrow mountain pass cuts through the peaks, the trail "
             "winding between towering granite walls streaked with iron "
             "ore. Cold wind funnels through the gap, carrying the scent "
             "of pine and snow from the heights above."),
        ],
    )

    rooms["s_gate"] = create_object(
        RoomGateway,
        key="Southern Descent",
        attributes=[
            ("desc",
             "The mountain trail descends steeply here, switchbacking "
             "down through thinning alpine forest. Far below, the land "
             "flattens toward the distant glitter of the coast."),
        ],
    )

    # ── Connecting room ───────────────────────────────────────────────

    rooms["mountain_road"] = create_object(
        RoomBase,
        key="Dwarven Mountain Road",
        attributes=[
            ("desc",
             "A broad stone road, expertly cut into the mountainside by "
             "dwarven engineers. The flagstones are worn smooth by "
             "centuries of cart traffic. Peaks rise on all sides, their "
             "summits lost in cloud."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect_bidirectional_exit(rooms["sw_gate"], rooms["mountain_road"], "northeast")
    connect_bidirectional_exit(rooms["mountain_road"], rooms["s_gate"], "south")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.MOUNTAIN.value)

    print("  Ironback Peaks scaffold complete (3 rooms).\n")

    return {
        "sw_gate": rooms["sw_gate"],
        "s_gate": rooms["s_gate"],
    }


def soft_deploy():
    """Wipe and rebuild Ironback Peaks zone."""
    clean_zone()
    build_zone()
