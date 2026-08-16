"""
Shared zone management utilities — DEPRECATED.

============================================================
DEPRECATION NOTICE — 2026-05-17

World deployment happens exclusively through the
evennia-world-builder library (`wb_build`) from now on. The
`wb_build` pipeline cleans by `wb_deployment_file` tag (per
authored YAML file), which is finer-grained than the zone-tag
sweep this module provided.

The body of `clean_zone()` plus its helpers and the evennia
imports it relied on are believed to be non-active code and
have been commented out below pending live testing and
confirmation. Marked for future deletion — once a server
build confirms `wb_build` covers every previous use case,
this module can be removed entirely.

Previously used by:
    - world.game_world.zones.millholm.soft_deploy.clean_zone()
    - world.game_world.zones.book_zones.hundred_acre_wood.
      clean_hundred_acre_wood()
Both callers are now themselves dormant (same deprecation
pattern).
============================================================
"""

# from evennia import ObjectDB, search_tag
# 
# 
# SYSTEM_KEYS = {"Limbo", "Purgatory", "nft_recycle_bin"}
# 
# 
# def _get_limbo():
#     return ObjectDB.objects.get(id=2)
# 
# 
# def _is_player_character(obj):
#     return obj.is_typeclass("typeclasses.actors.character.FCMCharacter", exact=False)
# 
# 
# def _is_system_room(obj):
#     return obj.key in SYSTEM_KEYS
# 
# 
# def _return_fungibles_to_reserve(obj):
#     if not hasattr(obj, "get_gold"):
#         return
#     gold = obj.get_gold()
#     if gold and gold > 0:
#         try:
#             obj.return_gold_to_reserve(gold)
#         except Exception as err:
#             print(f"  [WARN] Could not return {gold} gold from {obj}: {err}")
#     if hasattr(obj, "get_all_resources"):
#         for rid, amt in list(obj.get_all_resources().items()):
#             if amt > 0:
#                 try:
#                     obj.return_resource_to_reserve(rid, amt)
#                 except Exception as err:
#                     print(
#                         f"  [WARN] Could not return resource {rid} x{amt} "
#                         f"from {obj}: {err}"
#                     )
# 
# 
# def clean_zone(zone_key: str):
#     """
#     Remove all game-world objects tagged to zone_key while preserving:
#       - Player accounts and characters
#       - Items/gold/resources in character inventories or account banks
#       - System rooms (Limbo, Purgatory, RecycleBin)
#       - Global scripts
# 
#     Safe to call on a zone that has never been built — returns immediately if
#     no rooms carry the zone tag.
#     """
#     limbo = _get_limbo()
#     print(f"=== CLEANING ZONE: {zone_key} ===\n")
# 
#     zone_rooms = list(search_tag(zone_key, category="zone"))
#     if not zone_rooms:
#         print(f"  No rooms tagged '{zone_key}'. Nothing to clean.\n")
#         return
# 
#     # ── 1. Evacuate players ──────────────────────────────────────────
#     print("[1/5] Evacuating players to Limbo...")
#     evacuated = 0
#     for room in zone_rooms:
#         for obj in list(room.contents):
#             if _is_player_character(obj):
#                 obj.location = limbo
#                 obj.msg("|y[System] The world shimmers and reforms around you.|n")
#                 evacuated += 1
#     print(f"  Moved {evacuated} player(s) to Limbo.")
# 
#     # ── 2. Delete mobs and NPCs ──────────────────────────────────────
#     print("[2/5] Deleting mobs and NPCs...")
#     mob_count = 0
#     for room in zone_rooms:
#         for obj in list(room.contents):
#             if obj.is_typeclass(
#                 "typeclasses.actors.mob", exact=False
#             ) or obj.is_typeclass("typeclasses.actors.npc", exact=False):
#                 _return_fungibles_to_reserve(obj)
#                 obj.delete()
#                 mob_count += 1
#     print(f"  Deleted {mob_count} mob(s)/NPC(s).")
# 
#     # ── 3. Delete orphaned items ─────────────────────────────────────
#     print("[3/5] Deleting orphaned items...")
#     item_count = 0
#     for room in zone_rooms:
#         for obj in list(room.contents):
#             if not obj.pk:
#                 continue
#             if _is_player_character(obj):
#                 continue
#             if _is_system_room(obj):
#                 continue
#             _return_fungibles_to_reserve(obj)
#             obj.delete()
#             item_count += 1
#     print(f"  Deleted {item_count} item(s).")
# 
#     # ── 4. Delete exits ──────────────────────────────────────────────
#     print("[4/5] Deleting exits...")
#     exit_count = 0
#     for obj in list(ObjectDB.objects.filter(db_typeclass_path__contains="exits")):
#         if not obj.pk:
#             continue
#         if obj.location and _is_system_room(obj.location):
#             continue
#         if obj.location and obj.location.tags.get(category="zone") == zone_key:
#             obj.delete()
#             exit_count += 1
#     print(f"  Deleted {exit_count} exit(s).")
# 
#     # ── 5. Delete rooms ──────────────────────────────────────────────
#     print("[5/5] Deleting rooms...")
#     room_count = 0
#     deleted_ids = set()
#     for room in zone_rooms:
#         if room.id in deleted_ids:
#             continue
#         if _is_system_room(room):
#             continue
#         _return_fungibles_to_reserve(room)
#         deleted_ids.add(room.id)
#         try:
#             room.delete()
#         except Exception:
#             continue  # already deleted by cascade
#         room_count += 1
#     print(f"  Deleted {room_count} room(s).")
# 
#     print(f"\n=== ZONE '{zone_key}' CLEAN COMPLETE ===\n")
