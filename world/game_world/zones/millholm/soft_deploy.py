"""
Millholm Zone — soft deploy script.

All Millholm content is built by the YAML world-builder library
reading from shard0/millholm/ in the fcm-world repo (see
WORLDBUILDER_REPO in settings.py). Mob populations are maintained
by the evennia-mob-spawner library reading from shard0/millholm/ in
the fcm-mobs repo (MOB_SPAWNER_REPO) and loaded via the operator
command `ms_load`. Neither is managed from this module.

What this module does:
  - clean_zone(): wipe Millholm objects (used to recycle the zone
    while iterating)
  - build_zone(): kept as a callsite for deploy_world.py compatibility;
    no longer creates spawn scripts (those are operator-driven via
    `ms_load shard=shard0 zone=millholm`)

Usage (Evennia shell):
    from world.game_world.zones.millholm.soft_deploy import (
        soft_deploy, build_zone, clean_zone,
    )
    soft_deploy()      # wipe Millholm + rebuild
    clean_zone()       # wipe only
    build_zone()       # status print only
"""

from world.game_world.zone_utils import clean_zone as _clean_zone

ZONE_KEY = "millholm"


def clean_zone():
    """Remove all Millholm zone objects, preserving players and system rooms."""
    _clean_zone(ZONE_KEY)


def build_zone(one_way_limbo=False):
    """
    Status print for the Millholm zone build.

    Rooms / exits / NPCs / fixtures are built from YAML via the
    world-builder library (`wb_build`). Mob populations are deployed
    operator-side via the mob-spawner library (`ms_load shard=shard0
    zone=millholm`). Nothing to do here at build time — this function
    is kept as a callsite for `deploy_world.py` compatibility.

    Args:
        one_way_limbo: Unused legacy parameter, kept for caller
            compatibility until deploy_world.py is also cleaned up.
    """
    print("=== MILLHOLM ZONE BUILD ===")
    print("  Rooms / exits / NPCs / fixtures: built via wb_build")
    print("  Mob populations: deploy with `ms_load shard=shard0 zone=millholm`")
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
