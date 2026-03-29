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

from typeclasses.terrain.exits.conditional_dungeon_exit import ConditionalDungeonExit
from typeclasses.terrain.exits.exit_vertical_aware import ExitVerticalAware
from typeclasses.terrain.exits.procedural_dungeon_exit import ProceduralDungeonExit
from utils.exit_helpers import connect, connect_door
from world.game_world.zone_utils import clean_zone as _clean_zone
from world.game_world.zones.millholm.faerie_hollow import build_faerie_hollow
from world.game_world.zones.millholm.farms import build_millholm_farms
from world.game_world.zones.millholm.fixtures import place_millholm_fixtures
from world.game_world.zones.millholm.mine import build_millholm_mine
from world.game_world.zones.millholm.mobs import spawn_millholm_mobs
from world.game_world.zones.millholm.cemetery import build_millholm_cemetery
from world.game_world.zones.millholm.northern import build_millholm_northern
from world.game_world.zones.millholm.npcs import spawn_millholm_npcs
from world.game_world.zones.millholm.rooftops import build_millholm_rooftops
from world.game_world.zones.millholm.sewers import build_millholm_sewers
from world.game_world.zones.millholm.southern import build_millholm_southern
from world.game_world.zones.millholm.town import build_millholm_town
from world.game_world.zones.millholm.woods import build_millholm_woods

ZONE_KEY = "millholm"


def clean_zone():
    """Remove all Millholm zone objects, preserving players and system rooms."""
    _clean_zone(ZONE_KEY)


def build_zone(one_way_limbo=False):
    """
    Build the Millholm zone from scratch.

    Args:
        one_way_limbo: If True, create only a one-way exit from Limbo to the
            inn (players can't walk back to Limbo). Default False (two-way).

    Returns a gateway_rooms dict for cross-zone wiring in deploy_world.py.
    All gateways are currently stubs — exits will be wired as adjacent zones
    are built.

    Gateway keys:
        "east_gate"          — eastern exit toward Ironback Peaks / Cloverfen (BASIC)
        "shadowsward_gate"   — southern exit toward The Shadowsward (SKILLED)
    """
    print("=== BUILDING MILLHOLM ZONE ===\n")

    # ── Districts ────────────────────────────────────────────────────
    print("[1] Building Millholm Town...")
    town_rooms = build_millholm_town(one_way_limbo=one_way_limbo)

    print("[2] Building Millholm Farms...")
    farm_rooms = build_millholm_farms(town_rooms)

    print("[3] Building Millholm Woods...")
    woods_rooms = build_millholm_woods(town_rooms)

    print("[3b] Building Millholm Cemetery...")
    cemetery_rooms = build_millholm_cemetery()

    print("[3c] Connecting north road → cemetery gates...")
    connect(town_rooms["north_road"], cemetery_rooms["cemetery_gates"], "west")

    print("[4] Building Millholm Sewers...")
    sewer_rooms = build_millholm_sewers()

    # ── Cross-district hidden doors (town ↔ sewers) ──────────────────
    print("[4a] Connecting cellar → sewer entrance (hidden)...")
    door_ab, _ = connect_door(
        town_rooms["cellar"],
        sewer_rooms["sewer_entrance"],
        "west",
        key="a concealed stone door",
        closed_ab=(
            "The west wall of the cellar appears to be solid stone, "
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
        open_ba="The stone door stands open, revealing a dimly lit cellar.",
        door_name="stone door",
    )
    door_ab.is_hidden = True
    door_ab.find_dc = 10

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
    door_ab2.find_dc = 10

    # ── Cellar access + Rat Cellar quest trigger ────────────────────
    print("[4c] Setting up Cellar and Rat Cellar quest entrance...")
    import world.dungeons.templates.rat_cellar  # noqa: F401

    # Door from stairwell down to the permanent cellar
    connect_door(
        town_rooms["cellar_stairwell"],
        town_rooms["cellar"],
        "south",
        key="a small wooden door",
        closed_ab=(
            "A small wooden door leads south into the cellar."
        ),
        open_ab=(
            "Cool, damp air drifts up through the open cellar door."
        ),
        closed_ba=(
            "A small wooden door leads north to the stairwell."
        ),
        open_ba=(
            "The stairwell is visible through the open door."
        ),
        door_name="door",
    )

    # Dungeon trigger exit from the permanent cellar into the procedural
    # rat cellar dungeon. Quest-gated — dungeon when quest active, empty
    # back cellar when not.
    cellar_trigger = create_object(
        ConditionalDungeonExit,
        key="a dark passage",
        location=town_rooms["cellar"],
        destination=town_rooms["cellar"],  # self-referential (dungeon path)
    )
    cellar_trigger.set_direction("south")
    cellar_trigger.dungeon_template_id = "rat_cellar"
    cellar_trigger.condition_type = "quest_active"
    cellar_trigger.condition_key = "rat_cellar"
    cellar_trigger.alternate_destination_id = town_rooms["back_cellar"].id

    # Return exit from back cellar to cellar
    back_cellar_return = create_object(
        ExitVerticalAware,
        key="Cellar",
        location=town_rooms["back_cellar"],
        destination=town_rooms["cellar"],
    )
    back_cellar_return.set_direction("north")

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
        ProceduralDungeonExit,
        key="Deep Woods",
        location=entry_room,
        destination=entry_room,
    )
    trigger_in.set_direction("north")
    trigger_in.dungeon_template_id = "deep_woods_passage"
    trigger_in.dungeon_destination_room_id = clearing_room.id

    print("[6b] Connecting deep woods clearing → entry (procedural passage)...")
    trigger_out = create_object(
        ProceduralDungeonExit,
        key="Deep Woods",
        location=clearing_room,
        destination=clearing_room,
    )
    trigger_out.set_direction("west")
    trigger_out.dungeon_template_id = "deep_woods_passage"
    trigger_out.dungeon_destination_room_id = entry_room.id

    print("[6c] Connecting deep woods clearing → miners' camp (procedural passage)...")
    trigger_to_mine = create_object(
        ProceduralDungeonExit,
        key="Deep Woods",
        location=clearing_room,
        destination=clearing_room,
    )
    trigger_to_mine.set_direction("east")
    trigger_to_mine.dungeon_template_id = "deep_woods_passage"
    trigger_to_mine.dungeon_destination_room_id = miners_camp.id

    print("[6d] Connecting miners' camp → deep woods clearing (procedural passage)...")
    trigger_from_mine = create_object(
        ProceduralDungeonExit,
        key="Deep Woods",
        location=miners_camp,
        destination=miners_camp,
    )
    trigger_from_mine.set_direction("west")
    trigger_from_mine.dungeon_template_id = "deep_woods_passage"
    trigger_from_mine.dungeon_destination_room_id = clearing_room.id

    # ── Southern District ────────────────────────────────────────────
    print("[7] Building Millholm Southern District...")
    southern_rooms = build_millholm_southern()

    print("[7a] Connecting town south gate → southern district...")
    connect(town_rooms["south_gate"], southern_rooms["countryside_road"], "south")

    print("[7b] Connecting farm south fork → southern countryside...")
    connect(farm_rooms["south_fork_end"], southern_rooms["countryside_road"], "east")

    # ── Rooftops District ──────────────────────────────────────────────
    print("[8] Building Millholm Rooftops...")
    roof_rooms = build_millholm_rooftops()

    # ── Cross-district: town ↔ rooftops ──────────────────────────────
    print("[8a] Connecting Artisan's Way W1 → Sagging Rooftop (fly)...")
    exit_aw1_roof = create_object(
        ExitVerticalAware,
        key="the rooftops",
        location=town_rooms["artisans_way_w1"],
        destination=roof_rooms["rooftops_w1"],
    )
    exit_aw1_roof.set_direction("north")
    exit_aw1_roof.required_min_height = 1
    exit_aw1_roof.required_max_height = 2
    exit_aw1_roof.arrival_heights = {1: 0, 2: 1}

    exit_roof_aw1 = create_object(
        ExitVerticalAware,
        key="Artisan's Way below",
        location=roof_rooms["rooftops_w1"],
        destination=town_rooms["artisans_way_w1"],
    )
    exit_roof_aw1.set_direction("south")
    exit_roof_aw1.arrival_heights = {0: 1, 1: 2}

    print("[8b] Connecting vacant workshop → back alley (hidden door)...")
    door_ab, door_ba = connect_door(
        town_rooms["vacant_w1"], town_rooms["back_alley"], "north",
        key="a sheet of corrugated iron",
        closed_ab=(
            "A large sheet of rusted corrugated iron leans against the "
            "back wall. It doesn't quite sit flush."
        ),
        open_ab=(
            "The corrugated iron has been pushed aside, revealing a "
            "narrow gap leading to an alley behind the workshop."
        ),
        closed_ba=(
            "A sheet of corrugated iron covers a gap in the wall "
            "to the south."
        ),
        open_ba=(
            "Through the gap in the wall you can see a dusty workshop."
        ),
        door_name="iron",
    )
    door_ab.is_hidden = True
    door_ab.find_dc = 2  # TODO: restore to 16 after testing
    door_ba.required_min_height = 0
    door_ba.required_max_height = 0

    print("[8c] Connecting back alley → Sagging Rooftop (climb)...")
    exit_to_roof = create_object(
        ExitVerticalAware,
        key="the rooftops",
        location=town_rooms["back_alley"],
        destination=roof_rooms["rooftops_w1"],
    )
    exit_to_roof.set_direction("south")
    exit_to_roof.required_min_height = 1
    exit_to_roof.required_max_height = 1
    exit_to_roof.arrival_heights = {1: 0}

    exit_to_alley = create_object(
        ExitVerticalAware,
        key="the alley below",
        location=roof_rooms["rooftops_w1"],
        destination=town_rooms["back_alley"],
    )
    exit_to_alley.set_direction("down")
    exit_to_alley.arrival_heights = {0: 0}

    print("[8d] Connecting Gareth's bedroom → General Store Rooftop (hidden wardrobe)...")
    door_wardrobe, door_wardrobe_ba = connect_door(
        town_rooms["gareth_bedroom"], roof_rooms["rooftops_store"], "east",
        key="an oak wardrobe",
        closed_ab=(
            "A massive oak wardrobe stands against the far wall, "
            "slightly too big for the room."
        ),
        open_ab=(
            "The wardrobe has been pushed aside, revealing a low "
            "doorway cut into the wall behind it. Cold air and the "
            "smell of rain-soaked slate drift through the gap."
        ),
        closed_ba=(
            "A low doorway leads west, blocked by the back of a "
            "large wardrobe."
        ),
        open_ba=(
            "Through the low doorway you can see a dimly lit bedroom."
        ),
        door_name="wardrobe",
    )
    door_wardrobe.is_hidden = True
    door_wardrobe.find_dc = 2  # TODO: restore to 16 after testing
    # Wardrobe exit only at ground level (height 1 goes to Gareth's roof)
    door_wardrobe_ba.required_min_height = 0
    door_wardrobe_ba.required_max_height = 0

    # ── Northern District (lake) ─────────────────────────────────────
    print("[9] Building Millholm Northern...")
    northern_rooms = build_millholm_northern()

    print("[9a] Connecting north road → lake track...")
    connect(town_rooms["north_road"], northern_rooms["lake_track"], "north")

    print("[9b] Connecting lake track ↔ lake shore (procedural passage)...")
    import world.dungeons.templates.lake_passage  # noqa: F401

    trigger_to_lake = create_object(
        ProceduralDungeonExit,
        key="a rough track",
        location=northern_rooms["lake_track"],
        destination=northern_rooms["lake_track"],
    )
    trigger_to_lake.set_direction("north")
    trigger_to_lake.dungeon_template_id = "lake_passage"
    trigger_to_lake.dungeon_destination_room_id = northern_rooms["lake_shore"].id

    trigger_from_lake = create_object(
        ProceduralDungeonExit,
        key="a rough track",
        location=northern_rooms["lake_shore"],
        destination=northern_rooms["lake_shore"],
    )
    trigger_from_lake.set_direction("south")
    trigger_from_lake.dungeon_template_id = "lake_passage"
    trigger_from_lake.dungeon_destination_room_id = northern_rooms["lake_track"].id

    # ── Fixtures, NPCs, Mobs ─────────────────────────────────────────
    place_millholm_fixtures(
        town_rooms, farm_rooms, woods_rooms, sewer_rooms, southern_rooms,
        mine_rooms,
    )
    spawn_millholm_npcs()
    spawn_millholm_mobs()

    print("=== MILLHOLM ZONE BUILD COMPLETE ===\n")

    # Return gateway rooms for cross-zone wiring in deploy_world.py.
    # Exits will be added to these rooms when adjacent zones are built.
    return {
        "east_gate": woods_rooms["east_gate"],
        "shadowsward_gate": southern_rooms["shadowsward_gate"],
    }


def soft_deploy():
    """Wipe and rebuild the Millholm zone."""
    clean_zone()
    build_zone()
