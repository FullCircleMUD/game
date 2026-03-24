"""
Guildmere Island Zone — soft deploy script.

Cartography tier: MASTER (sea)
Access: Sea — Seamanship MASTER + Carrack from Arcane Sanctum / Oldbone Island

Scaffold: 4 rooms (2 gateways + 2 connecting rooms).

Gateway keys:
    "dock"    — sea routes (Arcane Sanctum, Oldbone Island, Vaathari)
    "n_gate"  — overland to Atlantis (MASTER, dive/water breathing)
"""

from evennia import create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.room_base import RoomBase
from typeclasses.terrain.rooms.room_gateway import RoomGateway
from utils.exit_helpers import connect
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "guildmere_island"
DISTRICT = "guildmere_island_travel"


def clean_zone():
    """Remove all Guildmere Island zone objects."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """Build Guildmere Island travel scaffold. Returns gateway_rooms dict."""
    print("=== BUILDING GUILDMERE ISLAND ZONE (scaffold) ===\n")

    rooms = {}

    # ── Gateways ──────────────────────────────────────────────────────

    rooms["dock"] = create_object(
        RoomGateway,
        key="Guildmere Harbour",
        attributes=[
            ("desc",
             "A grand harbour of white stone curves around a sheltered "
             "lagoon. The water is impossibly clear, and the ships moored "
             "here are of a quality rarely seen elsewhere — gleaming hulls "
             "and silk sails. The island rises steeply behind the port, "
             "its slopes covered in manicured gardens and guild halls."),
        ],
    )

    rooms["n_gate"] = create_object(
        RoomGateway,
        key="Coral Beach",
        attributes=[
            ("desc",
             "A secluded beach of crushed coral at the island's northern "
             "tip. The water here is deep and dark, dropping away sharply "
             "from the shore. Strange currents swirl below the surface, "
             "and the faint glow of something vast and ancient shimmers "
             "in the depths."),
        ],
    )

    # ── Connecting rooms ──────────────────────────────────────────────

    rooms["guild_promenade"] = create_object(
        RoomBase,
        key="Guild Promenade",
        attributes=[
            ("desc",
             "A wide promenade of polished marble connects the harbour "
             "to the island's interior. Guild halls of every trade line "
             "the way — their banners displaying symbols of commerce, "
             "craft, and scholarship. The wealth here is understated "
             "but unmistakable."),
        ],
    )

    rooms["coastal_path"] = create_object(
        RoomBase,
        key="Coastal Path",
        attributes=[
            ("desc",
             "A winding path follows the island's rocky coastline north. "
             "Tropical flowers spill over low stone walls, and the sea "
             "crashes against rocks far below. The path narrows as it "
             "approaches a secluded beach."),
        ],
    )

    # ── Exits ─────────────────────────────────────────────────────────

    connect(rooms["dock"], rooms["guild_promenade"], "west")
    connect(rooms["guild_promenade"], rooms["coastal_path"], "north")
    connect(rooms["coastal_path"], rooms["n_gate"], "north")

    # ── Tags ──────────────────────────────────────────────────────────

    for room in rooms.values():
        room.tags.add(ZONE_KEY, category="zone")
        room.tags.add(DISTRICT, category="district")

    rooms["dock"].set_terrain(TerrainType.COASTAL.value)
    rooms["n_gate"].set_terrain(TerrainType.COASTAL.value)
    rooms["guild_promenade"].set_terrain(TerrainType.URBAN.value)
    rooms["coastal_path"].set_terrain(TerrainType.COASTAL.value)

    print("  Guildmere Island scaffold complete (4 rooms).\n")

    return {
        "dock": rooms["dock"],
        "n_gate": rooms["n_gate"],
    }


def soft_deploy():
    """Wipe and rebuild Guildmere Island zone."""
    clean_zone()
    build_zone()
