"""
Build the game world — the real Millholm zone.

Usage (from Evennia shell / @py):
    from world.game_world.build_game_world import build_game_world
    build_game_world()
"""

from evennia import create_object, search_object

from typeclasses.terrain.exits.dungeon_trigger_exit import DungeonTriggerExit
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.terrain.exits.quest_dungeon_trigger_exit import (
    QuestDungeonTriggerExit,
)
from utils.exit_helpers import connect_door
from world.game_world.millholm_faerie_hollow import build_faerie_hollow
from world.game_world.millholm_farms import build_millholm_farms
from world.game_world.millholm_fixtures import place_millholm_fixtures
from world.game_world.spawn_millholm_mobs import spawn_millholm_mobs
from world.game_world.spawn_millholm_npcs import spawn_millholm_npcs
from world.game_world.millholm_mine import build_millholm_mine
from world.game_world.millholm_sewers import build_millholm_sewers
from world.game_world.millholm_southern import build_millholm_southern
from world.game_world.millholm_town import build_millholm_town
from world.game_world.millholm_woods import build_millholm_woods


RECYCLE_BIN_KEY = "nft_recycle_bin"
PURGATORY_KEY = "Purgatory"
def _ensure_system_room(key, typeclass_path, desc=None):
    """Create a system room if it doesn't already exist."""
    existing = search_object(key, exact=True)
    if existing:
        print(f"  {key} already exists: {existing[0].dbref}")
        return existing[0]

    from evennia import create_object
    room = create_object(typeclass_path, key=key)
    if desc:
        room.db.desc = desc
    room.tags.add("system_zone", category="zone")
    room.tags.add("system_district", category="district")
    print(f"  Created {key}: {room.dbref}")
    return room


def build_game_world():
    """Build the full game world."""
    print("=== BUILDING GAME WORLD ===\n")

    # Ensure system rooms exist (shared with test world)
    _ensure_system_room(
        RECYCLE_BIN_KEY,
        "typeclasses.terrain.rooms.room_recycle_bin.RoomRecycleBin",
        "A hidden room where orphaned NFT items are despawned and recycled.",
    )
    _ensure_system_room(
        PURGATORY_KEY,
        "typeclasses.terrain.rooms.room_purgatory.RoomPurgatory",
    )

    # Build districts
    print("[1] Building Millholm Town...")
    town_rooms = build_millholm_town()

    print("[2] Building Millholm Farms...")
    farm_rooms = build_millholm_farms(town_rooms)

    print("[3] Building Millholm Woods...")
    woods_rooms = build_millholm_woods(town_rooms)

    print("[4] Building Millholm Sewers...")
    sewer_rooms = build_millholm_sewers()

    # ── Cross-district hidden doors (town ↔ sewers) ───────────────────
    print("[4a] Connecting cellar stairwell → sewer entrance (hidden)...")
    door_ab, door_ba = connect_door(
        town_rooms["cellar_stairwell"], sewer_rooms["sewer_entrance"], "west",
        key="a concealed stone door",
        closed_ab=(
            "The west wall of the stairwell appears to be solid stone, "
            "though moisture seeps through some of the mortar joints."
        ),
        open_ab=(
            "The concealed door stands open, revealing the damp passage "
            "to the sewers beyond."
        ),
        closed_ba=(
            "A heavy stone door blocks the passage east, fitted to look "
            "like part of the sewer wall."
        ),
        open_ba=(
            "The stone door stands open, revealing a dimly lit stairwell."
        ),
        door_name="door",
    )
    door_ab.is_hidden = True
    door_ab.find_dc = 16

    print("[4b] Connecting abandoned house → old cistern (hidden)...")
    door_ab2, door_ba2 = connect_door(
        town_rooms["abandoned_house"], sewer_rooms["old_cistern"], "down",
        key="a trapdoor",
        closed_ab=(
            "The floorboards here are warped and uneven. One section "
            "seems slightly different from the rest."
        ),
        open_ab=(
            "A trapdoor in the floor stands open, a rusted ladder "
            "descending into a cistern below."
        ),
        closed_ba=(
            "A wooden trapdoor is set into the ceiling far above, "
            "accessible by a rusted ladder."
        ),
        open_ba=(
            "The trapdoor above hangs open, the abandoned house "
            "visible through the gap."
        ),
        door_name="trapdoor",
    )
    door_ab2.is_hidden = True
    door_ab2.find_dc = 18

    # ── Rat Cellar quest trigger (cellar_stairwell → instanced cellar) ──
    print("[4c] Setting up Rat Cellar quest entrance...")
    import world.dungeons.templates.rat_cellar  # noqa: F401

    cellar_trigger = create_object(
        QuestDungeonTriggerExit,
        key="a small wooden door",
        location=town_rooms["cellar_stairwell"],
        destination=town_rooms["cellar_stairwell"],  # self-referential
    )
    cellar_trigger.aliases.add("s")
    cellar_trigger.aliases.add("south")
    cellar_trigger.aliases.add("door")
    cellar_trigger.dungeon_template_id = "rat_cellar"
    cellar_trigger.quest_key = "rat_cellar"
    cellar_trigger.fallback_destination_id = town_rooms["cellar"].id

    # Return exit from permanent cellar (post-quest access)
    cellar_return = create_object(
        ExitVerticalAware,
        key="the cellar stairwell",
        location=town_rooms["cellar"],
        destination=town_rooms["cellar_stairwell"],
    )
    cellar_return.set_direction("north")

    # Abandoned Mine (static district — clearing ↔ mine passages wired below)
    print("[5] Building Millholm Abandoned Mine...")
    mine_rooms = build_millholm_mine()

    # Faerie Hollow (deep woods clearing + invisible faerie entrance)
    print("[6] Building Faerie Hollow...")
    faerie_rooms = build_faerie_hollow()

    # ── Deep Woods procedural passages (entry ↔ clearing) ─────────────
    # Ensure the template module is imported so it's registered.
    import world.dungeons.templates.deep_woods_passage  # noqa: F401

    entry_room = woods_rooms["deep_woods_entry"]
    clearing_room = faerie_rooms["deep_woods_clearing"]

    # Passage 1: entry → clearing (inbound — walk north into deep woods)
    print("[6a] Connecting deep woods entry → clearing (procedural passage)...")
    trigger_in = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=entry_room,
        destination=entry_room,  # self-referential (dungeon system pattern)
    )
    trigger_in.aliases.add("n")
    trigger_in.aliases.add("north")
    trigger_in.dungeon_template_id = "deep_woods_passage"
    trigger_in.dungeon_destination_room_id = clearing_room.id

    # Passage 2: clearing → entry (outbound — walk west to return)
    print("[6b] Connecting deep woods clearing → entry (procedural passage)...")
    trigger_out = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=clearing_room,
        destination=clearing_room,  # self-referential
    )
    trigger_out.aliases.add("w")
    trigger_out.aliases.add("west")
    trigger_out.dungeon_template_id = "deep_woods_passage"
    trigger_out.dungeon_destination_room_id = entry_room.id

    # ── Deep Woods procedural passages (clearing ↔ miners_camp) ─────────
    miners_camp = mine_rooms["miners_camp"]

    # Passage 3: clearing → miners_camp (inbound — walk east toward mine)
    print("[6c] Connecting deep woods clearing → miners' camp (procedural passage)...")
    trigger_to_mine = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=clearing_room,
        destination=clearing_room,  # self-referential
    )
    trigger_to_mine.aliases.add("e")
    trigger_to_mine.aliases.add("east")
    trigger_to_mine.dungeon_template_id = "deep_woods_passage"
    trigger_to_mine.dungeon_destination_room_id = miners_camp.id

    # Passage 4: miners_camp → clearing (outbound — walk west to return)
    print("[6d] Connecting miners' camp → deep woods clearing (procedural passage)...")
    trigger_from_mine = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=miners_camp,
        destination=miners_camp,  # self-referential
    )
    trigger_from_mine.aliases.add("w")
    trigger_from_mine.aliases.add("west")
    trigger_from_mine.dungeon_template_id = "deep_woods_passage"
    trigger_from_mine.dungeon_destination_room_id = clearing_room.id

    # Southern District (rougher town, countryside, moonpetal fields, gnoll territory, barrow)
    print("[7] Building Millholm Southern District...")
    southern_rooms = build_millholm_southern()

    # ── Cross-district connections (town/farms → southern) ───────────
    from utils.exit_helpers import connect

    print("[7a] Connecting town south gate → southern district...")
    connect(town_rooms["south_gate"], southern_rooms["countryside_road"], "south")

    print("[7b] Connecting farm south fork → southern countryside...")
    connect(farm_rooms["south_fork_end"], southern_rooms["countryside_road"], "east")

    # World fixtures (signs, monuments, interactables)
    place_millholm_fixtures(town_rooms, farm_rooms, woods_rooms, sewer_rooms)

    # NPCs
    spawn_millholm_npcs()

    # Mobs
    spawn_millholm_mobs()

    print("=== GAME WORLD BUILD COMPLETE ===")
