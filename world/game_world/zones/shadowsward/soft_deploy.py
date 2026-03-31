"""
The Shadowsward Zone — soft deploy script.

Cartography tier: SKILLED
Access: Overland from Millholm (NE gate)

Scaffold: 3 rooms (2 gateways + 1 normal room).

Gateway keys:
    "ne_gate"  — toward Millholm / Cloverfen (SKILLED cartography)
    "s_gate"   — toward Shadowroot / Aethenveil (EXPERT / MASTER cartography)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "shadowsward"
DISTRICT = "shadowsward_travel"


def clean_zone():
    """Remove all The Shadowsward zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build The Shadowsward travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING THE SHADOWSWARD ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateway ───────────────────────────────────────────────────────

    rooms["ne_gate"] = create_object(
        RoomGateway,
        key="Frontier Outpost",
        attributes=[
            ("desc",
             "A fortified outpost marks the northern edge of the "
             "Shadowsward. Wooden palisades surround a muddy yard where "
             "grim-faced soldiers keep watch. The road northeast leads "
             "back toward civilisation; southward lies open, wind-scoured "
             "grassland dotted with watchtowers."),
        ],
    )

    rooms["s_gate"] = create_object(
        RoomGateway,
        key="Southern Frontier",
        attributes=[
            ("desc",
             "The watchtowers thin out here at the southern edge of the "
             "Shadowsward. Beyond the last palisade, the grassland gives "
             "way to darker terrain — blackened forest to the west and "
             "shimmering haze to the south."),
        ],
    )

    # ── Placeholder room ──────────────────────────────────────────────

    rooms["watchtower_road"] = create_object(
        RoomBase,
        key="Watchtower Road",
        attributes=[
            ("desc",
             "A packed-earth road runs between distant watchtowers, "
             "their signal fires dark in the daylight. The grassland "
             "stretches flat and featureless to the horizon. An uneasy "
             "silence hangs over the frontier."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect_bidirectional_exit(rooms["ne_gate"], rooms["watchtower_road"], "south")
    connect_bidirectional_exit(rooms["watchtower_road"], rooms["s_gate"], "south")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.PLAINS.value)

    print("  The Shadowsward scaffold complete (3 rooms).\n")

    return {
        "ne_gate": rooms["ne_gate"],
        "s_gate": rooms["s_gate"],
    }


def soft_deploy():
    """Wipe and rebuild The Shadowsward zone."""
    clean_zone()
    build_zone()
