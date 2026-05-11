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
from utils.exit_helpers import connect_bidirectional_exit, connect_bidirectional_door_exit
from world.game_world.zone_utils import clean_zone as _clean_zone
from world.game_world.zones.millholm.faerie_hollow import build_faerie_hollow
from world.game_world.zones.millholm.fixtures import place_millholm_fixtures
from world.game_world.zones.millholm.mine import build_millholm_mine
from world.game_world.zones.millholm.mobs import spawn_millholm_mobs
from world.game_world.zones.millholm.northern import build_millholm_northern
from world.game_world.zones.millholm.npcs import spawn_millholm_npcs
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

    # Farms ported to YAML: shard0/millholm/farms/{roads,wheat-farm,
    # cotton-farm,abandoned-farm,secret-tunnel,npc_bramble,npc_tilly}.yaml.
    # All cross-district exits wired in YAML:
    #   - farms ↔ town (roads.yaml id 2 ↔ west-old-trade-way.yaml id 27)
    #   - farms ↔ southern (roads.yaml id 52 ↔ forest-north.yaml id 4)

    print("[3] Building Millholm Woods...")
    woods_rooms = build_millholm_woods(town_rooms)

    # Cemetery ported to YAML: shard0/millholm/cemetery/cemetery.yaml.
    # north_road → cemetery_gates cross-district exit is wired in
    # town/north-road.yaml id 9 ↔ cemetery.yaml id 2.

    # Sewers ported to YAML: shard0/millholm/sewers/sewers.yaml (rooms
    # + the thieves' gauntlet trap door, tripwire, hidden levers, key,
    # chest, guild token) plus npc_gareth/npc_vex/npc_whisper.yaml.
    # The two cross-district hidden doors are wired in YAML:
    #   - cellar (harvest-moon id 27) ↔ sewer_entrance (sewers id 3)
    #     stone door, hidden cellar side, find_dc 10
    #   - abandoned_house (west-old-trade-way id 26) ↔ old_cistern
    #     (sewers id 34) trapdoor, hidden abandoned-house side, find_dc 10

    # ── Cellar access + Rat Cellar quest trigger ────────────────────
    print("[4c] Setting up Cellar and Rat Cellar quest entrance...")
    import world.dungeons.templates.rat_cellar  # noqa: F401

    # Door from stairwell down to the permanent cellar
    connect_bidirectional_door_exit(
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
    cellar_trigger.alternate_destination = town_rooms["back_cellar"]

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
    # Southern ported to YAML: shard0/millholm/southern/{forest-north,
    # forest-south,gnolls,barrow,raven_sage,bandit_camp,
    # moonpetal-sage-side,moonpetal-bandit-side}.yaml — 144 rooms
    # total. All 6 southern_woods_passage procedural-passage pairs
    # are wired via YAML `links:` blocks setting
    # dungeon_destination_room_id on each ProceduralDungeonExit
    # (forest grid anchors ↔ mini-area interfaces, sibling-pair
    # mini-areas). Cross-district exits in YAML:
    #   - town south_gate (south-road.yaml id 83) ↔ countryside_road
    #     (forest-north.yaml id 1)
    #   - farms south_fork_end (roads.yaml id 52) ↔ countryside_road
    #     (forest-north.yaml id 4)
    #   - southern_approach (gnolls.yaml id 35) ↔ shadowsward_gate
    #     (gateways/shadowsward_gate.yaml id 1, north exit id 2)
    # The shadowsward_gate room itself is in gateways/, so it's
    # returned from this build via a YAML lookup if needed by
    # deploy_world.

    # ── Rooftops District ──────────────────────────────────────────────
    # Ported to YAML: shard0/millholm/rooftops/rooftops.yaml (rooms +
    # internal exits) plus the three cross-district connections
    # (artisans_way_w1 fly-up, back_alley climb + corrugated iron door,
    # Gareth's wardrobe). All exits and door pairs are now wired in YAML.

    # ── Northern District (lake) ─────────────────────────────────────
    print("[9] Building Millholm Northern...")
    northern_rooms = build_millholm_northern()

    print("[9a] Connecting north road → lake track...")
    connect_bidirectional_exit(town_rooms["north_road"], northern_rooms["lake_track"], "north")

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
    # TODO: place_millholm_fixtures is temporarily disabled — its
    # signature still expects farm_rooms and sewer_rooms dicts which
    # no longer exist (those districts now build via YAML). The
    # fixtures that were placed by Python need to be validated against
    # YAML (most are likely already in YAML as room `contents` entries)
    # and fixtures.py should be retired here. Tracked in the Python →
    # YAML cleanup sweep.
    # place_millholm_fixtures(town_rooms, woods_rooms, southern_rooms, mine_rooms)
    spawn_millholm_npcs()
    spawn_millholm_mobs()

    print("=== MILLHOLM ZONE BUILD COMPLETE ===\n")

    # TODO: deploy_world.py still does `millholm["east_gate"].destinations
    # = [...]` and `millholm["shadowsward_gate"].destinations = [...]` to
    # set interzone destinations. Both gateway rooms now live in YAML
    # (millholm/gateways/east_gate.yaml + shadowsward_gate.yaml) with
    # their `destinations` lists already filled via YAML `links:` —
    # so the Python override is now redundant. Once deploy_world.py is
    # updated to drop the Python overrides, this return value can go.
    # For now, return empty dict — deploy_world will fail at the
    # `.destinations = [...]` lines until those are also cleaned up.
    # (Branch is set up for the purpose, breakage during transition
    # is expected.)
    return {}


def soft_deploy():
    """Wipe and rebuild the Millholm zone."""
    clean_zone()
    build_zone()
