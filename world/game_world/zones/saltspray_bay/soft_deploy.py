"""
Saltspray Bay Zone — soft deploy script.

Cartography tier: SKILLED
Access: Overland from Ironback Peaks or Cloverfen (W gate)

Scaffold: 2 rooms (1 gateway + 1 normal room). Temporary endpoint —
more gateways (dock, overland south) will be added when expanding.

Gateway keys:
    "w_gate"  — toward Ironback Peaks / Cloverfen (SKILLED cartography)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "saltspray_bay"
DISTRICT = "saltspray_bay_travel"


def clean_zone():
    """Remove all Saltspray Bay zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Saltspray Bay travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING SALTSPRAY BAY ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateway ───────────────────────────────────────────────────────

    rooms["w_gate"] = create_object(
        RoomGateway,
        key="Western Approach",
        attributes=[
            ("desc",
             "The road crests a final hill and the great harbour of "
             "Saltspray Bay spreads before you. Masts crowd the wharves "
             "below, and the tang of salt and tar carries on the breeze. "
             "The road descends toward the city gates."),
        ],
    )

    # ── Placeholder room ──────────────────────────────────────────────

    rooms["harbour_road"] = create_object(
        RoomBase,
        key="Harbour Road",
        attributes=[
            ("desc",
             "A wide cobbled road winds down toward the harbour. "
             "Warehouses and chandleries line the way, their doors "
             "propped open to catch the sea breeze. The bustle of a "
             "thriving port town surrounds you."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect(rooms["w_gate"], rooms["harbour_road"], "east")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.COASTAL.value)

    print("  Saltspray Bay scaffold complete (2 rooms).\n")

    return {
        "w_gate": rooms["w_gate"],
    }


def soft_deploy():
    """Wipe and rebuild Saltspray Bay zone."""
    clean_zone()
    build_zone()
