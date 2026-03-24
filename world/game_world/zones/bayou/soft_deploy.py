"""
The Bayou Zone — soft deploy script.

Cartography tier: SKILLED
Access: Overland from Cloverfen / Saltspray Bay (N gate)
        Overland to Kashoryu (EXPERT) / Aethenveil (MASTER) (S gate)

Scaffold: 3 rooms (2 gateways + 1 connecting room).

Gateway keys:
    "n_gate"  — toward Cloverfen / Saltspray Bay (SKILLED cartography)
    "s_gate"  — toward Kashoryu (EXPERT) / Aethenveil (MASTER)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "bayou"
DISTRICT = "bayou_travel"


def clean_zone():
    """Remove all Bayou zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build The Bayou travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING THE BAYOU ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateways ──────────────────────────────────────────────────────

    rooms["n_gate"] = create_object(
        RoomGateway,
        key="Northern Fen",
        attributes=[
            ("desc",
             "The swamp thins here, giving way to firmer ground and "
             "clearer sky to the north. Moss-draped cypresses stand "
             "like sentinels along the border between the Bayou and "
             "the civilised lands beyond."),
        ],
    )

    rooms["s_gate"] = create_object(
        RoomGateway,
        key="Deep Bayou Crossing",
        attributes=[
            ("desc",
             "A rickety boardwalk crosses the deepest part of the swamp. "
             "The water is black and still, and strange lights flicker "
             "in the mist. Beyond the crossing, trails lead south toward "
             "warmer lands and ancient forests."),
        ],
    )

    # ── Connecting room ───────────────────────────────────────────────

    rooms["swamp_village"] = create_object(
        RoomBase,
        key="Stilt Village",
        attributes=[
            ("desc",
             "A ramshackle village built on wooden stilts above the "
             "murky water. Rope bridges connect platforms between "
             "ancient mangroves. The air is thick with humidity and "
             "the drone of insects. Locals eye you with quiet suspicion."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect(rooms["n_gate"], rooms["swamp_village"], "south")
    connect(rooms["swamp_village"], rooms["s_gate"], "south")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.SWAMP.value)

    print("  The Bayou scaffold complete (3 rooms).\n")

    return {
        "n_gate": rooms["n_gate"],
        "s_gate": rooms["s_gate"],
    }


def soft_deploy():
    """Wipe and rebuild The Bayou zone."""
    clean_zone()
    build_zone()
