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

from typeclasses.scripts.zone_spawn_script import ZoneSpawnScript
from world.game_world.zone_utils import clean_zone as _clean_zone
from world.game_world.zones.millholm.faerie_hollow import build_faerie_hollow
from world.game_world.zones.millholm.mine import build_millholm_mine

ZONE_KEY = "millholm"


def clean_zone():
    """Remove all Millholm zone objects, preserving players and system rooms."""
    _clean_zone(ZONE_KEY)


def build_zone(one_way_limbo=False):
    """
    Build the (residual) Python parts of the Millholm zone.

    Most of Millholm now builds from YAML via the world-builder library —
    see the comment block in build_zone() for the full district inventory.
    The Python build path remaining here is just the two unported districts
    (mine, faerie_hollow) plus the four deep_woods_passage procedural exits
    whose far-side endpoints still live in Python.

    Args:
        one_way_limbo: Unused (was used by the old build_millholm_town).
            Kept for caller compatibility; will be removed when
            deploy_world.py is updated.
    """
    print("=== BUILDING MILLHOLM ZONE ===\n")

    # All major districts are now built by the YAML world-builder
    # library reading from shard0/millholm/ — see WORLDBUILDER_REPO in
    # settings.py. The Python build path below covers only the two
    # remaining districts that haven't been ported yet (mine,
    # faerie_hollow), plus the four deep_woods_passage procedural
    # exits whose far-side endpoints (deep_woods_clearing, miners_camp)
    # still come from Python.
    #
    # YAML-ported districts (no Python needed):
    #   - town            shard0/millholm/town/*.yaml (8 files +
    #                     16 npc_*.yaml NPCs, 67 rooms, the rat_cellar
    #                     ConditionalDungeonExit and cellar↔sewer door
    #                     pairs all in harvest-moon.yaml)
    #   - farms           shard0/millholm/farms/*.yaml (7 files,
    #                     71 rooms + 2 shopkeeper NPCs)
    #   - woods           shard0/millholm/woods/*.yaml (track, woods,
    #                     + npc_bjorn/_buckshaw/_thackery, 94 rooms)
    #   - cemetery        shard0/millholm/cemetery/cemetery.yaml
    #   - sewers          shard0/millholm/sewers/*.yaml (sewers +
    #                     npc_gareth/_vex/_whisper)
    #   - rooftops        shard0/millholm/rooftops/rooftops.yaml
    #   - northern (lake) shard0/millholm/lake/lake.yaml + lake_track
    #                     in town/north-road.yaml + sailing_club +
    #                     canadia/far_shore gateways
    #   - southern        shard0/millholm/southern/*.yaml (8 files,
    #                     144 rooms, all 6 southern_woods_passage
    #                     procedural pairs wired via YAML links)
    #   - lake_passage    procedural exits at lake.yaml id 69 +
    #                     town/north-road.yaml id 13 (both ends in YAML)
    #   - cross-district exits in YAML: cellar↔sewer, abandoned_house↔
    #     cistern, north_road↔cemetery_gates, north_road↔lake_track,
    #     south_gate↔countryside_road, south_fork_end↔countryside_road,
    #     southern_approach↔shadowsward_gate, artisans_way↔rooftops fly,
    #     back_alley↔rooftops climb, gareth's wardrobe↔rooftops_store.

    # ── Mine and Faerie Hollow (still Python) ────────────────────────
    print("[5] Building Millholm Abandoned Mine...")
    mine_rooms = build_millholm_mine()

    print("[6] Building Faerie Hollow...")
    faerie_rooms = build_faerie_hollow()

    # ── Deep Woods procedural passages ──────────────────────────────
    # TODO: the four deep_woods_passage procedural exits are stubbed
    # during the Python→YAML transition. They wire:
    #   - woods deep_woods_entry (now in track.yaml id 130) ↔
    #     faerie_hollow deep_woods_clearing (still Python)
    #   - faerie_hollow deep_woods_clearing ↔ mine miners_camp (still
    #     Python)
    # The woods-side endpoint needs a YAML/search lookup once these
    # passages are re-wired. The faerie + mine endpoints stay in Python
    # until those districts are ported (NEEDS_YAML_PORT flags at the top
    # of faerie_hollow.py and mine.py). Original implementation kept in
    # git history (pre-removal).

    # ── Zone spawn scripts ───────────────────────────────────────────
    # ZoneSpawnScript.create_for_zone reads world/spawns/<zone>.json and
    # creates a persistent population-maintenance script for that area.
    # The YAML world tags rooms with `mob_area` so the spawn script can
    # locate valid spawn rooms by tag query.
    print("--- Creating Millholm Spawn Scripts ---")
    for zone_key in (
        "millholm_farms",
        "millholm_woods",
        "millholm_sewers",
        "millholm_mine",
        "millholm_southern",
        "millholm_cemetery",
        "millholm_lake",
        "millholm_town",
        "millholm_rooftops",
    ):
        script = ZoneSpawnScript.create_for_zone(zone_key)
        if script:
            print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
        else:
            print(f"  [!] Failed to create {zone_key} spawn script")
    print("--- Millholm spawn script creation complete ---")

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
