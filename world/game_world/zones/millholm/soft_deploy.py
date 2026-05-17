"""
Millholm Zone — soft deploy script.

All Millholm content is now built by the YAML world-builder library
reading from shard0/millholm/ in the fcm-world repo (see
WORLDBUILDER_REPO in settings.py). The Python orchestration that
once lived here has been retired piece by piece as each district
was ported.

What this module still does:
  - clean_zone(): wipe Millholm objects (used to recycle the zone
    while iterating)
  - build_zone(): create the per-zone ZoneSpawnScript instances
    that maintain mob populations against the YAML world's
    mob_area room tags

Usage (Evennia shell):
    from world.game_world.zones.millholm.soft_deploy import (
        soft_deploy, build_zone, clean_zone,
    )
    soft_deploy()      # wipe Millholm + rebuild spawn scripts
    clean_zone()       # wipe only
    build_zone()       # rebuild spawn scripts only
"""

from typeclasses.scripts.zone_spawn_script import ZoneSpawnScript
from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "millholm"


def clean_zone():
    """Remove all Millholm zone objects, preserving players and system rooms."""
    _clean_zone(ZONE_KEY)


def build_zone(one_way_limbo=False):
    """
    (Re)create the Millholm zone's spawn scripts.

    All room/exit/NPC content is now built from YAML by the world-
    builder library; this function only sets up the per-area
    ZoneSpawnScript instances that maintain mob populations against
    the YAML world's mob_area tags.

    YAML-ported districts (each builds from shard0/millholm/<name>/):
      town, farms, woods, cemetery, sewers, rooftops, lake, southern,
      mine, faerie (= faerie_hollow + the static deep_woods_clearing
      that connects woods ↔ mine via the deep_woods_passage procedural).

    Procedural passages wired entirely in YAML:
      - rat_cellar       (ConditionalDungeonExit in harvest-moon.yaml)
      - southern_woods_passage (6 pairs across southern/*.yaml)
      - lake_passage     (lake.yaml ↔ town/north-road.yaml)
      - deep_woods_passage (woods/track.yaml ↔ faeries/faerie_hollow
                            .yaml ↔ mine/mine.yaml)

    Args:
        one_way_limbo: Unused legacy parameter, kept for caller
            compatibility until deploy_world.py is also cleaned up.
    """
    print("=== BUILDING MILLHOLM ZONE ===\n")
    print("  All Millholm rooms / exits / NPCs / fixtures now build")
    print("  from YAML via the world-builder library.")

    # ── Zone spawn scripts ──────────────────────────────────────────────
    # ZoneSpawnScript.create_for_zone reads world/spawns/<zone>.json and
    # creates a persistent population-maintenance script that finds spawn
    # rooms via mob_area tag queries against the YAML-deployed world.
    print("--- Creating Millholm Spawn Scripts ---")
    # All Millholm zones are being progressively MIGRATED to the
    # evennia-mob-spawner library. Source of truth: the fcm-mobs repo
    # (shard0/millholm/<file>.yaml). Loaded via
    # `ms_load shard=shard0 zone=millholm file=<name>`.
    # The JSON files in world/spawns/ are kept for reference until each
    # zone has been fully validated under the new system.
    for zone_key in (
        # All Millholm zones are disabled here for the migration. The
        # JSON spawn data remains in world/spawns/<zone>.json as the
        # porting reference. `town` has been ported to YAML
        # (fcm-mobs/shard0/millholm/town.yaml); the others are pending
        # — they will spawn no mobs until their YAML is in place.
        # "millholm_farms",      # PENDING port
        # "millholm_woods",      # PENDING port
        # "millholm_sewers",     # PENDING port
        # "millholm_mine",       # PENDING port
        # "millholm_southern",   # PENDING port
        # "millholm_cemetery",   # PENDING port
        # "millholm_lake",       # PENDING port
        # "millholm_town",       # PORTED → fcm-mobs/shard0/millholm/town.yaml
        # "millholm_rooftops",   # PENDING port
    ):
        script = ZoneSpawnScript.create_for_zone(zone_key)
        if script:
            print(f"  Created {script.key} ({len(script.db.spawn_table)} rules)")
        else:
            print(f"  [!] Failed to create {zone_key} spawn script")
    print("--- Millholm spawn script creation complete ---")

    print("=== MILLHOLM ZONE BUILD COMPLETE ===\n")

    # TODO: deploy_world.py still does
    #   millholm["east_gate"].destinations = [...]
    #   millholm["shadowsward_gate"].destinations = [...]
    # to set interzone destinations. Both gateway rooms now live in
    # YAML with their `destinations` lists already filled via the
    # gateway files' `links:` blocks, so those Python overrides are
    # redundant. Returning {} here breaks deploy_world's gateway
    # override lines — clean those up in their own pass when ready.
    return {}


def soft_deploy():
    """Wipe and rebuild the Millholm zone."""
    clean_zone()
    build_zone()
