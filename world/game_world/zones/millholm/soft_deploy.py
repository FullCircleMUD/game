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
from utils.exit_helpers import connect_bidirectional_exit, connect_bidirectional_door_exit
from world.game_world.zone_utils import clean_zone as _clean_zone
from world.game_world.zones.millholm.faerie_hollow import build_faerie_hollow
from world.game_world.zones.millholm.fixtures import place_millholm_fixtures
from world.game_world.zones.millholm.mine import build_millholm_mine
from world.game_world.zones.millholm.mobs import spawn_millholm_mobs
from world.game_world.zones.millholm.npcs import spawn_millholm_npcs
from world.game_world.zones.millholm.town import build_millholm_town

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

    # Woods ported to YAML: shard0/millholm/woods/{track,woods}.yaml
    # (94 rooms covering the forest_path_east spine, sawmill +
    # tannery + smelter RoomProcessing setups, 60-room Southern Woods
    # grid with RoomHarvesting for timber, 10-room Northern Woods
    # transition row, and the deep_woods_entry procedural-passage
    # anchor at track.yaml id 130). All cross-district exits in YAML:
    #   - forest_path_east ↔ town/east-old-trade-way (track.yaml id 1)
    #   - wooded_foothills ↔ gateways/east_gate.yaml
    # The deep_woods_passage procedural exits ([6a-d] below) reference
    # deep_woods_entry which is now in YAML only; soft_deploy will
    # need to fetch it via search/tag lookup once those passages are
    # also re-wired in YAML.

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
    # TODO: stubbed during the Python→YAML transition. The four
    # deep_woods_passage procedural exits ([6a/b/c/d]) wire:
    #   - woods deep_woods_entry (now in track.yaml id 130) ↔
    #     faerie_hollow deep_woods_clearing (Python)
    #   - faerie_hollow deep_woods_clearing ↔ mine miners_camp (Python)
    # The deep_woods_entry side will need a YAML/search lookup once
    # the passages are re-wired. The faerie + mine ends stay in Python
    # until those districts are also ported (NEEDS_YAML_PORT flags
    # at the top of faerie_hollow.py and mine.py).
    # Original implementation kept in git history (pre-removal).
    # clearing_room = faerie_rooms["deep_woods_clearing"]
    # miners_camp = mine_rooms["miners_camp"]
    # ... 4 × ProceduralDungeonExit creates ...

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
    # Ported to YAML:
    #   - lake.yaml: 16 lake-district rooms (shore + shallows + deep
    #     rows with WATER terrain, height/depth gating; underwater
    #     bloodmoss grotto with RoomHarvesting; boatyard RoomCrafting;
    #     wreck WorldChest fixture at vertical -2 in deep_dock).
    #   - town/north-road.yaml id 10: lake_track (millholm_town district
    #     per source).
    #   - gateways/sailing_club.yaml + canadia/gateways/far_shore.yaml:
    #     boat gateways, boat_level + food_cost conditions.
    # Cross-district / procedural exits wired in YAML:
    #   - north_road ↔ lake_track  (north-road.yaml internal pair)
    #   - lake_track ↔ lake_shore via lake_passage ProceduralDungeonExit
    #     (north-road.yaml id 13 + lake.yaml id 69, both with
    #     dungeon_destination_room_id links).

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
