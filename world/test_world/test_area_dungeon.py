"""
Spawn a dungeon entrance in the Thieves Guild for playtesting.

Run AFTER test_area_economic() has created the guild rooms.

Creates a DungeonEntranceRoom linked to the Cave of Trials template,
connected via a "down" exit from the Thieves Guild Entrance.

Usage (from Evennia):
    @py from world.test_world.test_area_dungeon import test_area_dungeon; test_area_dungeon()
"""

from evennia import ObjectDB, create_object

from enums.terrain_type import TerrainType
from typeclasses.terrain.rooms.dungeon.dungeon_entrance_room import DungeonEntranceRoom
from utils.exit_helpers import connect

# Ensure the cave template is registered
import world.dungeons.templates.cave_dungeon  # noqa: F401


ENTRANCE_KEY = "The Cavern Mouth"


def _find_room(key):
    """Find a room by exact key."""
    results = ObjectDB.objects.filter(db_key=key, db_typeclass_path__contains="room")
    if results.exists():
        return results.first()
    return None


def test_area_dungeon():
    """Spawn the dungeon entrance below the Thieves Guild."""

    print("\n=== Spawning Dungeon Entrance ===\n")

    thieves_guild = _find_room("Thieves Guild Entrance")
    if not thieves_guild:
        print("  ! Thieves Guild Entrance not found — run test_area_economic() first")
        return

    # Check if entrance already exists
    existing = _find_room(ENTRANCE_KEY)
    if existing:
        print(f"  Dungeon entrance already exists: {existing.dbref}")
        return

    # Create the dungeon entrance room
    entrance = create_object(
        DungeonEntranceRoom,
        key=ENTRANCE_KEY,
    )
    entrance.db.desc = (
        "A jagged crack in the cellar wall opens into darkness. "
        "Cold, damp air flows from the depths, carrying the faint "
        "smell of earth and something else... something bestial. "
        "A crude sign is scratched into the stone: 'Cave of Trials'. "
        "Only the brave — or foolish — venture below."
    )
    entrance.dungeon_template_id = "cave_of_trials"

    # Inherit zone/district from parent (Thieves Guild → guild_district)
    entrance.tags.add("test_economic_zone", category="zone")
    entrance.tags.add("guild_district", category="district")
    entrance.set_terrain(TerrainType.UNDERGROUND.value)

    print(f"  Created dungeon entrance: {entrance.dbref}")

    # Bidirectional exits between Thieves Guild and dungeon entrance
    connect(thieves_guild, entrance, "down",
            desc_ab="a dark crack in the wall", desc_ba="Thieves Guild")
    print("  Created exits: Thieves Guild <-> Dungeon Entrance")

    print("\n=== Dungeon Entrance Done ===")
    print("  Use 'enter dungeon' in The Cavern Mouth to start!")
    print("  Navigate 5 rooms deep to reach BINGO!\n")
