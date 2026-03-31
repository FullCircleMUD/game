"""
Scalded Waste Zone — soft deploy script.

Cartography tier: MASTER
Access: Overland from Aethenveil / Shadowroot (N gate)

Scaffold: 3 rooms (2 gateways + 1 normal room).

Gateway keys:
    "n_gate"  — toward Shadowroot / Aethenveil
    "s_gate"  — toward Zharavan (GRANDMASTER)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "scalded_waste"
DISTRICT = "scalded_waste_travel"


def clean_zone():
    """Remove all Scalded Waste zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Scalded Waste travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING SCALDED WASTE ZONE (scaffold) ===\n")

    rooms = {}

    rooms["n_gate"] = create_object(
        RoomGateway,
        key="Northern Escarpment",
        attributes=[
            ("desc",
             "A crumbling escarpment overlooks the blistered wasteland "
             "below. The ground is cracked and pale, radiating heat even "
             "in the shade. Trails north lead toward darker forests and "
             "the silver woods beyond."),
        ],
    )

    rooms["s_gate"] = create_object(
        RoomGateway,
        key="Southern Dust Road",
        attributes=[
            ("desc",
             "The dust road narrows to a faint track, half-buried by "
             "windblown sand. The wasteland gives way to something older "
             "and stranger — the air shimmers with mirages, and half-"
             "ruined towers are visible on the horizon."),
        ],
    )

    rooms["salt_flats"] = create_object(
        RoomBase,
        key="Salt Flats",
        attributes=[
            ("desc",
             "A blinding expanse of white salt stretches to the horizon. "
             "The ground crunches underfoot, and heat haze makes distant "
             "landmarks waver and dance. Bleached bones of enormous "
             "creatures jut from the crust at odd angles."),
        ],
    )

    connect_bidirectional_exit(rooms["n_gate"], rooms["salt_flats"], "south")
    connect_bidirectional_exit(rooms["salt_flats"], rooms["s_gate"], "south")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.DESERT.value)

    print("  Scalded Waste scaffold complete (3 rooms).\n")
    return {
        "n_gate": rooms["n_gate"],
        "s_gate": rooms["s_gate"],
    }


def soft_deploy():
    """Wipe and rebuild Scalded Waste zone."""
    clean_zone()
    build_zone()
