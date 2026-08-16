"""
Millholm Zone — soft deploy script (DEPRECATED).

============================================================
DEPRECATION NOTICE — 2026-05-17

All Millholm world content is built by the evennia-world-builder
library (`wb_build`) reading shard0/millholm/ in the fcm-world
repo. Mob populations are maintained by evennia-mob-spawner via
`ms_load shard=shard0 zone=millholm`. Neither is managed from
this module any longer.

Previous local helpers (clean_zone, build_zone, soft_deploy),
the ZONE_KEY constant, and the zone_utils import they depended
on are believed to be non-active code and have been commented
out below pending live testing and confirmation. Marked for
future deletion — once `wb_build` is confirmed to cover every
previous use case, this module can be removed entirely.

The previous `build_zone()` docstring noted gateway override
lines in the (now-deleted) deploy_world.py — those overrides
were already redundant with the YAML `links:` blocks on the
gateway files.
============================================================
"""

# from world.game_world.zone_utils import clean_zone as _clean_zone
# 
# ZONE_KEY = "millholm"
# 
# 
# def clean_zone():
#     """Remove all Millholm zone objects, preserving players and system rooms."""
#     _clean_zone(ZONE_KEY)
# 
# 
# def build_zone(one_way_limbo=False):
#     """
#     Status print for the Millholm zone build.
# 
#     Rooms / exits / NPCs / fixtures are built from YAML via the
#     world-builder library (`wb_build`). Mob populations are deployed
#     operator-side via the mob-spawner library (`ms_load shard=shard0
#     zone=millholm`). Nothing to do here at build time — this function
#     is kept as a callsite for `deploy_world.py` compatibility.
# 
#     Args:
#         one_way_limbo: Unused legacy parameter, kept for caller
#             compatibility until deploy_world.py is also cleaned up.
#     """
#     print("=== MILLHOLM ZONE BUILD ===")
#     print("  Rooms / exits / NPCs / fixtures: built via wb_build")
#     print("  Mob populations: deploy with `ms_load shard=shard0 zone=millholm`")
#     print("=== MILLHOLM ZONE BUILD COMPLETE ===\n")
# 
#     # TODO: deploy_world.py still does
#     #   millholm["east_gate"].destinations = [...]
#     #   millholm["shadowsward_gate"].destinations = [...]
#     # to set interzone destinations. Both gateway rooms now live in
#     # YAML with their `destinations` lists already filled via the
#     # gateway files' `links:` blocks, so those Python overrides are
#     # redundant. Returning {} here breaks deploy_world's gateway
#     # override lines — clean those up in their own pass when ready.
#     return {}
# 
# 
# def soft_deploy():
#     """Wipe and rebuild the Millholm zone."""
#     clean_zone()
#     build_zone()
