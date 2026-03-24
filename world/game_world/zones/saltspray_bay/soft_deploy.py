"""
Saltspray Bay Zone — soft deploy script.

Cartography tier: SKILLED
Access: Overland from Ironback Peaks or Cloverfen (W gate)
        Sea routes from dock (E gate)

Scaffold: 4 rooms (2 gateways + 2 connecting rooms).

Gateway keys:
    "w_gate"   — toward Ironback Peaks / Cloverfen / Bayou (SKILLED cartography)
    "dock"     — sea routes to islands and Kashoryu
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

    # ── Gateways ──────────────────────────────────────────────────────

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

    rooms["dock"] = create_object(
        RoomGateway,
        key="Saltspray Bay Docks",
        attributes=[
            ("desc",
             "The great harbour of Saltspray Bay stretches before you, "
             "a forest of masts and rigging. Merchant vessels from distant "
             "lands crowd the wharves, their crews shouting in a dozen "
             "tongues. The harbourmaster's office overlooks it all from "
             "a stone tower."),
        ],
    )

    # ── Connecting rooms ──────────────────────────────────────────────

    rooms["harbour_road"] = create_object(
        RoomBase,
        key="Harbour Road",
        attributes=[
            ("desc",
             "A wide cobbled road winds through the heart of Saltspray "
             "Bay. Warehouses and chandleries line the way, their doors "
             "propped open to catch the sea breeze. The bustle of a "
             "thriving port town surrounds you."),
        ],
    )

    rooms["market_square"] = create_object(
        RoomBase,
        key="Saltspray Market Square",
        attributes=[
            ("desc",
             "An open market square bustles with trade. Stalls sell "
             "exotic spices, bolts of silk, and strange fruits from "
             "distant shores. The harbour is visible down the hill "
             "to the east, and roads lead west and south."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect(rooms["w_gate"], rooms["market_square"], "east")
    connect(rooms["market_square"], rooms["harbour_road"], "east")
    connect(rooms["harbour_road"], rooms["dock"], "east")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.COASTAL.value)

    rooms["market_square"].set_terrain(TerrainType.URBAN.value)
    rooms["harbour_road"].set_terrain(TerrainType.URBAN.value)

    print("  Saltspray Bay scaffold complete (4 rooms).\n")

    return {
        "w_gate": rooms["w_gate"],
        "dock": rooms["dock"],
    }


def soft_deploy():
    """Wipe and rebuild Saltspray Bay zone."""
    clean_zone()
    build_zone()
