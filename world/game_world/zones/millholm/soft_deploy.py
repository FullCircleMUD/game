"""
Millholm Zone — soft deploy script.

Builds all Millholm districts and their intra-zone connections. Can be run
independently to iterate on Millholm without touching other zones.

Usage (Evennia shell):
    from world.game_world.zones.millholm.soft_deploy import soft_deploy, build_zone, clean_zone
    soft_deploy()      # wipe Millholm + rebuild
    clean_zone()       # wipe only
    build_zone()       # rebuild only (assumes zone already clean)
"""

from evennia import create_object

from typeclasses.terrain.exits.dungeon_trigger_exit import DungeonTriggerExit
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.terrain.exits.quest_dungeon_trigger_exit import QuestDungeonTriggerExit
from utils.exit_helpers import connect, connect_door
from world.game_world.zone_utils import clean_zone as _clean_zone
from world.game_world.zones.millholm.faerie_hollow import build_faerie_hollow
from world.game_world.zones.millholm.farms import build_millholm_farms
from world.game_world.zones.millholm.fixtures import place_millholm_fixtures
from world.game_world.zones.millholm.mine import build_millholm_mine
from world.game_world.zones.millholm.mobs import spawn_millholm_mobs
from world.game_world.zones.millholm.npcs import spawn_millholm_npcs
from world.game_world.zones.millholm.sewers import build_millholm_sewers
from world.game_world.zones.millholm.southern import build_millholm_southern
from world.game_world.zones.millholm.town import build_millholm_town
from world.game_world.zones.millholm.woods import build_millholm_woods

ZONE_KEY = "millholm"


def clean_zone():
    """Remove all Millholm zone objects, preserving players and system rooms."""
    _clean_zone(ZONE_KEY)


def build_zone():
    """
    Build the Millholm zone from scratch.

    Returns a gateway_rooms dict for cross-zone wiring in deploy_world.py.
    All gateways are currently stubs — exits will be wired as adjacent zones
    are built.

    Gateway keys:
        "shadowsward_gate"   — southern exit toward The Shadowsward (SKILLED)
    """
    print("=== BUILDING MILLHOLM ZONE ===\n")

    # ── Districts ────────────────────────────────────────────────────
    print("[1] Building Millholm Town...")
    town_rooms = build_millholm_town()

    print("[2] Building Millholm Farms...")
    farm_rooms = build_millholm_farms(town_rooms)

    print("[3] Building Millholm Woods...")
    woods_rooms = build_millholm_woods(town_rooms)

    print("[4] Building Millholm Sewers...")
    sewer_rooms = build_millholm_sewers()

    # ── Cross-district hidden doors (town ↔ sewers) ──────────────────
    print("[4a] Connecting cellar stairwell → sewer entrance (hidden)...")
    door_ab, _ = connect_door(
        town_rooms["cellar_stairwell"],
        sewer_rooms["sewer_entrance"],
        "west",
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
        open_ba="The stone door stands open, revealing a dimly lit stairwell.",
        door_name="door",
    )
    door_ab.is_hidden = True
    door_ab.find_dc = 16

    print("[4b] Connecting abandoned house → old cistern (hidden)...")
    door_ab2, _ = connect_door(
        town_rooms["abandoned_house"],
        sewer_rooms["old_cistern"],
        "down",
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
            "The trapdoor above hangs open, the abandoned house visible through the gap."
        ),
        door_name="trapdoor",
    )
    door_ab2.is_hidden = True
    door_ab2.find_dc = 18

    # ── Rat Cellar quest trigger ─────────────────────────────────────
    print("[4c] Setting up Rat Cellar quest entrance...")
    import world.dungeons.templates.rat_cellar  # noqa: F401

    cellar_trigger = create_object(
        QuestDungeonTriggerExit,
        key="a small wooden door",
        location=town_rooms["cellar_stairwell"],
        destination=town_rooms["cellar_stairwell"],
    )
    cellar_trigger.aliases.add("s")
    cellar_trigger.aliases.add("south")
    cellar_trigger.aliases.add("door")
    cellar_trigger.dungeon_template_id = "rat_cellar"
    cellar_trigger.quest_key = "rat_cellar"
    cellar_trigger.fallback_destination_id = town_rooms["cellar"].id

    cellar_return = create_object(
        ExitVerticalAware,
        key="the cellar stairwell",
        location=town_rooms["cellar"],
        destination=town_rooms["cellar_stairwell"],
    )
    cellar_return.set_direction("north")

    # ── Mine and Faerie Hollow ───────────────────────────────────────
    print("[5] Building Millholm Abandoned Mine...")
    mine_rooms = build_millholm_mine()

    print("[6] Building Faerie Hollow...")
    faerie_rooms = build_faerie_hollow()

    # ── Deep Woods procedural passages ──────────────────────────────
    import world.dungeons.templates.deep_woods_passage  # noqa: F401

    entry_room = woods_rooms["deep_woods_entry"]
    clearing_room = faerie_rooms["deep_woods_clearing"]
    miners_camp = mine_rooms["miners_camp"]

    print("[6a] Connecting deep woods entry → clearing (procedural passage)...")
    trigger_in = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=entry_room,
        destination=entry_room,
    )
    trigger_in.aliases.add("n")
    trigger_in.aliases.add("north")
    trigger_in.dungeon_template_id = "deep_woods_passage"
    trigger_in.dungeon_destination_room_id = clearing_room.id

    print("[6b] Connecting deep woods clearing → entry (procedural passage)...")
    trigger_out = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=clearing_room,
        destination=clearing_room,
    )
    trigger_out.aliases.add("w")
    trigger_out.aliases.add("west")
    trigger_out.dungeon_template_id = "deep_woods_passage"
    trigger_out.dungeon_destination_room_id = entry_room.id

    print("[6c] Connecting deep woods clearing → miners' camp (procedural passage)...")
    trigger_to_mine = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=clearing_room,
        destination=clearing_room,
    )
    trigger_to_mine.aliases.add("e")
    trigger_to_mine.aliases.add("east")
    trigger_to_mine.dungeon_template_id = "deep_woods_passage"
    trigger_to_mine.dungeon_destination_room_id = miners_camp.id

    print("[6d] Connecting miners' camp → deep woods clearing (procedural passage)...")
    trigger_from_mine = create_object(
        DungeonTriggerExit,
        key="Deep Woods",
        location=miners_camp,
        destination=miners_camp,
    )
    trigger_from_mine.aliases.add("w")
    trigger_from_mine.aliases.add("west")
    trigger_from_mine.dungeon_template_id = "deep_woods_passage"
    trigger_from_mine.dungeon_destination_room_id = clearing_room.id

    # ── Southern District ────────────────────────────────────────────
    print("[7] Building Millholm Southern District...")
    southern_rooms = build_millholm_southern()

    print("[7a] Connecting town south gate → southern district...")
    connect(town_rooms["south_gate"], southern_rooms["countryside_road"], "south")

    print("[7b] Connecting farm south fork → southern countryside...")
    connect(farm_rooms["south_fork_end"], southern_rooms["countryside_road"], "east")

    # ── Fixtures, NPCs, Mobs ─────────────────────────────────────────
    place_millholm_fixtures(town_rooms, farm_rooms, woods_rooms, sewer_rooms)
    spawn_millholm_npcs()
    spawn_millholm_mobs()

    print("=== MILLHOLM ZONE BUILD COMPLETE ===\n")

    # Return gateway rooms for cross-zone wiring in deploy_world.py.
    # Exits will be added to these rooms when adjacent zones are built.
    return {
        "shadowsward_gate": southern_rooms["shadowsward_gate"],
    }


def soft_deploy():
    """Wipe and rebuild the Millholm zone."""
    clean_zone()
    build_zone()
