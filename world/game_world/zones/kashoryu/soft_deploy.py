"""
Kashoryu Zone — soft deploy script.

Cartography tier: SKILLED (sea) / EXPERT (overland via Bayou)
Access: Sea from Saltspray Bay / islands (dock)
        Overland from Bayou (N gate)

Scaffold: 5 rooms (2 gateways + 3 connecting rooms).

Gateway keys:
    "n_gate"  — toward Bayou (EXPERT) / Aethenveil (MASTER)
    "dock"    — sea routes to islands and Saltspray Bay
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "kashoryu"
DISTRICT = "kashoryu_travel"


def clean_zone():
    """Remove all Kashoryu zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Kashoryu travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING KASHORYU ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateways ──────────────────────────────────────────────────────

    rooms["n_gate"] = create_object(
        RoomGateway,
        key="Northern Jungle Trail",
        attributes=[
            ("desc",
             "The jungle trail narrows as it climbs northward into "
             "thicker growth. Vines hang like curtains across the path, "
             "and the calls of exotic birds echo from the canopy. The "
             "swamps of the Bayou lie somewhere beyond."),
        ],
    )

    rooms["dock"] = create_object(
        RoomGateway,
        key="Kashoryu Harbour",
        attributes=[
            ("desc",
             "The tropical harbour of Kashoryu curves around a turquoise "
             "lagoon. Outrigger canoes and foreign trading vessels share "
             "the crystal-clear water. Palm trees shade the waterfront "
             "where merchants haggle over spices and silk."),
        ],
    )

    # ── Connecting rooms ──────────────────────────────────────────────

    rooms["temple_road"] = create_object(
        RoomBase,
        key="Temple Road",
        attributes=[
            ("desc",
             "A wide road paved with red stone leads through the heart "
             "of Kashoryu. Ornate temples and pagodas rise on both sides, "
             "their curved roofs glinting with gold leaf. Incense smoke "
             "drifts from open doorways."),
        ],
    )

    rooms["market_district"] = create_object(
        RoomBase,
        key="Kashoryu Market",
        attributes=[
            ("desc",
             "A vibrant open-air market fills a wide plaza. Stalls "
             "overflow with tropical fruit, carved jade, bolts of silk, "
             "and pungent spices. The harbour is visible downhill to "
             "the east."),
        ],
    )

    rooms["jungle_edge"] = create_object(
        RoomBase,
        key="Jungle Edge",
        attributes=[
            ("desc",
             "The city gives way to dense tropical jungle. Carved stone "
             "markers along the trail indicate the distance to various "
             "destinations. The air is heavy and sweet with the scent "
             "of frangipani."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect_bidirectional_exit(rooms["n_gate"], rooms["jungle_edge"], "south")
    connect_bidirectional_exit(rooms["jungle_edge"], rooms["temple_road"], "south")
    connect_bidirectional_exit(rooms["temple_road"], rooms["market_district"], "east")
    connect_bidirectional_exit(rooms["market_district"], rooms["dock"], "east")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["n_gate"].set_terrain(TerrainType.FOREST.value)
    rooms["jungle_edge"].set_terrain(TerrainType.FOREST.value)
    rooms["temple_road"].set_terrain(TerrainType.URBAN.value)
    rooms["market_district"].set_terrain(TerrainType.URBAN.value)
    rooms["dock"].set_terrain(TerrainType.COASTAL.value)

    print("  Kashoryu scaffold complete (5 rooms).\n")

    return {
        "n_gate": rooms["n_gate"],
        "dock": rooms["dock"],
    }


def soft_deploy():
    """Wipe and rebuild Kashoryu zone."""
    clean_zone()
    build_zone()
