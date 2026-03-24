"""
Port Shadowmere Zone — soft deploy script.

Cartography tier: SKILLED (sea)
Access: Sea — Seamanship SKILLED + Caravel from Saltspray Bay / Kashoryu

Scaffold: 2 rooms (1 dock gateway + 1 normal room).

Gateway keys:
    "dock"  — sea routes back to Saltspray Bay / Kashoryu
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "port_shadowmere"
DISTRICT = "port_shadowmere_travel"


def clean_zone():
    """Remove all Port Shadowmere zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Port Shadowmere travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING PORT SHADOWMERE ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Shadowmere Wharf",
        attributes=[
            ("desc",
             "A fog-shrouded wharf extends into grey water. Gas lamps "
             "flicker along the pier despite the hour — in Port "
             "Shadowmere, it is always twilight. Dark-hulled ships "
             "creak at their moorings, and hooded figures move along "
             "the waterfront with quiet purpose."),
        ],
    )

    rooms["twilight_street"] = create_object(
        RoomBase,
        key="Twilight Street",
        attributes=[
            ("desc",
             "A narrow cobbled street winds inland from the wharf. "
             "The buildings lean together overhead, blocking what little "
             "light filters through the perpetual gloom. Shop signs "
             "swing in a breeze that carries the scent of strange "
             "incense and old secrets."),
        ],
    )

    connect(rooms["dock"], rooms["twilight_street"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.COASTAL.value)

    rooms["twilight_street"].set_terrain(TerrainType.URBAN.value)

    print("  Port Shadowmere scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild Port Shadowmere zone."""
    clean_zone()
    build_zone()
