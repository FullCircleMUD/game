"""
Shadowroot Zone — soft deploy script.

Cartography tier: EXPERT
Access: Overland from Shadowsward (E gate)

Scaffold: 2 rooms (1 gateway + 1 normal room).

Gateway keys:
    "e_gate"  — toward Shadowsward / Scalded Waste / Aethenveil
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "shadowroot"
DISTRICT = "shadowroot_travel"


def clean_zone():
    """Remove all Shadowroot zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Shadowroot travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING SHADOWROOT ZONE (scaffold) ===\n")

    rooms = {}

    rooms["e_gate"] = create_object(
        RoomGateway,
        key="Blighted Threshold",
        attributes=[
            ("desc",
             "The corrupted forest ends abruptly at a jagged tree line. "
             "Blackened trunks give way to scorched earth and open sky. "
             "The air still tastes of ash, but the oppressive canopy is "
             "behind you. Trails lead east toward the frontier."),
        ],
    )

    rooms["deep_blight"] = create_object(
        RoomBase,
        key="Deep Blight",
        attributes=[
            ("desc",
             "Twisted, blackened trees press close on every side, their "
             "bark oozing dark sap. No birdsong reaches this deep — only "
             "the creak of tortured wood and the occasional rustle of "
             "something moving through the undergrowth."),
        ],
    )

    connect(rooms["e_gate"], rooms["deep_blight"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.FOREST.value)

    print("  Shadowroot scaffold complete (2 rooms).\n")
    return {"e_gate": rooms["e_gate"]}


def soft_deploy():
    """Wipe and rebuild Shadowroot zone."""
    clean_zone()
    build_zone()
