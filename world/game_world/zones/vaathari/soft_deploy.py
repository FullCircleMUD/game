"""
Vaathari Zone — soft deploy script.

Cartography tier: GRANDMASTER (sea)
Access: Sea — Seamanship GRANDMASTER + Galleon from Guildmere Island

Scaffold: 2 rooms (1 dock gateway + 1 normal room). Temporary endpoint.

Gateway keys:
    "dock"  — sea route back to Guildmere Island
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect_bidirectional_exit
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "vaathari"
DISTRICT = "vaathari_travel"


def clean_zone():
    """Remove all Vaathari zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Vaathari travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING VAATHARI ZONE (scaffold) ===\n")

    rooms = {}

    rooms["dock"] = create_object(
        RoomGateway,
        key="Vaathari Landfall",
        attributes=[
            ("desc",
             "A black stone quay juts into churning grey waters. The "
             "crossing from Guildmere has brought you to the edge of "
             "the known world. Beyond the dock, a land of impossible "
             "scale stretches to the horizon — mountains that pierce "
             "the clouds, forests of trees taller than towers. The air "
             "tastes of ozone and something older than history."),
        ],
    )

    rooms["threshold"] = create_object(
        RoomBase,
        key="The Threshold",
        attributes=[
            ("desc",
             "A vast stone archway marks the entrance to the continent "
             "of Vaathari. Carvings in a language no living scholar can "
             "read cover every surface. The ground trembles faintly "
             "underfoot, as though the land itself is aware of your "
             "presence."),
        ],
    )

    connect_bidirectional_exit(rooms["dock"], rooms["threshold"], "west")

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")
        room.set_terrain(TerrainType.COASTAL.value)

    print("  Vaathari scaffold complete (2 rooms).\n")
    return {"dock": rooms["dock"]}


def soft_deploy():
    """Wipe and rebuild Vaathari zone."""
    clean_zone()
    build_zone()
