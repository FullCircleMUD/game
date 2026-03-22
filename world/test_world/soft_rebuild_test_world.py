"""
Soft-rebuild: wipe the test world and rebuild it WITHOUT touching
player accounts, characters, or their inventories.

Works for both initial setup AND subsequent resets — soft_reset()
harmlessly finds nothing on a fresh database, then build_test_world()
creates everything as normal.

Usage (from Evennia shell / @py):
    from world.test_world.soft_rebuild_test_world import soft_rebuild
    soft_rebuild()

Or just the cleanup half:
    from world.test_world.soft_rebuild_test_world import soft_reset
    soft_reset()
"""

from evennia import ObjectDB, search_object, search_tag

from world.test_world.build_test_world import build_test_world


# ── Zone tags applied by build scripts ──────────────────────────────
TEST_ZONE_TAGS = [
    "test_economic_zone",
    "test_water_fly_zone",
    "arena_zone",
]

# System rooms that must NEVER be deleted
SYSTEM_KEYS = {"Limbo", "Purgatory", "Cemetery", "nft_recycle_bin"}


def _get_limbo():
    """Return the Limbo room (Evennia's default room, always id=2)."""
    results = search_object("Limbo", exact=True)
    if results:
        return results[0]
    return ObjectDB.objects.get(id=2)


def _is_player_character(obj):
    """True if obj is a player character (not NPC/mob)."""
    return obj.is_typeclass(
        "typeclasses.actors.character.FCMCharacter", exact=False
    )


def _is_system_room(obj):
    """True if obj is a system room that must be preserved."""
    return obj.key in SYSTEM_KEYS


def _return_fungibles_to_reserve(obj):
    """
    Return any gold/resources on an object back to the vault reserve.

    Uses the FungibleInventoryMixin's properly-wired methods which
    dispatch to the correct service calls (GoldService.despawn /
    ResourceService.despawn for WORLD objects) and update both the
    local Evennia state and the blockchain mirror DB.
    """
    if not hasattr(obj, "get_gold"):
        return

    gold = obj.get_gold()
    if gold and gold > 0:
        try:
            obj.return_gold_to_reserve(gold)
        except Exception as err:
            print(f"  [WARN] Could not return {gold} gold from {obj}: {err}")

    if hasattr(obj, "get_all_resources"):
        for rid, amt in list(obj.get_all_resources().items()):
            if amt > 0:
                try:
                    obj.return_resource_to_reserve(rid, amt)
                except Exception as err:
                    print(
                        f"  [WARN] Could not return resource {rid} x{amt} "
                        f"from {obj}: {err}"
                    )


def soft_reset():
    """
    Delete all test-world objects while preserving:
      - Player accounts and characters
      - Items/gold/resources in character inventories or account banks
      - System rooms (Limbo, Purgatory, Cemetery, RecycleBin)
      - Global scripts (regeneration_service, hunger_service)
    """
    limbo = _get_limbo()
    print("=== SOFT RESET — preserving players and system rooms ===\n")

    # ── 1. Evacuate players to Limbo ────────────────────────────────
    print("[1/7] Evacuating players to Limbo...")
    evacuated = 0
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__contains="actors.character"
    ):
        if obj.location and obj.location != limbo:
            obj.location = limbo
            obj.msg("|y[System] The world shimmers and reforms around you.|n")
            evacuated += 1
    print(f"  Moved {evacuated} player(s) to Limbo.")

    # ── 2. Clean up dungeon instances ───────────────────────────────
    print("[2/7] Cleaning up dungeon instances...")
    dungeon_count = 0
    for script in ObjectDB.objects.filter(
        db_typeclass_path__contains="dungeon_instance"
    ):
        try:
            if hasattr(script, "cleanup"):
                script.cleanup()
            script.delete()
            dungeon_count += 1
        except Exception as err:
            print(f"  [WARN] Dungeon cleanup error: {err}")
    print(f"  Cleaned up {dungeon_count} dungeon instance(s).")

    # ── 3. Delete mobs ──────────────────────────────────────────────
    print("[3/7] Deleting mobs...")
    mob_count = 0
    mob_patterns = ["actors.mob", "mobs.rabbit", "mobs.wolf", "mobs.dire_wolf"]
    seen_ids = set()
    for pattern in mob_patterns:
        for obj in ObjectDB.objects.filter(
            db_typeclass_path__contains=pattern
        ):
            if obj.id in seen_ids:
                continue
            seen_ids.add(obj.id)
            _return_fungibles_to_reserve(obj)
            obj.delete()
            mob_count += 1
    print(f"  Deleted {mob_count} mob(s).")

    # ── 4. Delete NPCs ──────────────────────────────────────────────
    print("[4/7] Deleting NPCs...")
    npc_count = 0
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__contains="actors.npc"
    ):
        _return_fungibles_to_reserve(obj)
        obj.delete()
        npc_count += 1
    print(f"  Deleted {npc_count} NPC(s).")

    # ── 5. Delete world objects & items NOT held by players ─────────
    print("[5/7] Deleting orphaned items and world objects...")
    item_count = 0

    # Corpses
    for obj in ObjectDB.objects.filter(
        db_typeclass_path__contains="world_objects.corpse"
    ):
        _return_fungibles_to_reserve(obj)
        obj.delete()
        item_count += 1

    # World objects (signs, chests, keys, XP buttons, etc.)
    for obj in list(ObjectDB.objects.filter(
        db_typeclass_path__contains="world_objects"
    )):
        if not obj.pk:
            continue  # already deleted in cascade
        # Skip if inside a player's inventory
        if obj.location and _is_player_character(obj.location):
            continue
        obj.delete()
        item_count += 1

    # NFT items not on a player character or in an account bank
    for obj in list(ObjectDB.objects.filter(
        db_typeclass_path__contains="items."
    )):
        if not obj.pk:
            continue  # already deleted in cascade
        holder = obj.location
        # Preserve items held by players
        if holder and _is_player_character(holder):
            continue
        # Preserve items in account banks
        if holder and holder.is_typeclass(
            "typeclasses.accounts.account_bank.AccountBank", exact=False
        ):
            continue
        # NFT at_object_delete handles mirror DB cleanup
        obj.delete()
        item_count += 1

    print(f"  Deleted {item_count} item(s)/world object(s).")

    # ── 6. Delete exits ─────────────────────────────────────────────
    print("[6/7] Deleting exits...")
    exit_count = 0
    for obj in list(ObjectDB.objects.filter(
        db_typeclass_path__contains="exits"
    )):
        if not obj.pk:
            continue
        # Don't delete exits whose source is a system room
        if obj.location and _is_system_room(obj.location):
            continue
        obj.delete()
        exit_count += 1
    print(f"  Deleted {exit_count} exit(s).")

    # ── 7. Delete test-zone rooms ───────────────────────────────────
    print("[7/7] Deleting test-zone rooms...")
    room_count = 0
    deleted_ids = set()

    for zone_tag in TEST_ZONE_TAGS:
        rooms = search_tag(zone_tag, category="zone")
        for room in rooms:
            if room.id in deleted_ids:
                continue
            if _is_system_room(room):
                continue
            _return_fungibles_to_reserve(room)
            deleted_ids.add(room.id)
            room.delete()
            room_count += 1

    # Catch any rooms tagged with mob_area but not a zone tag
    for mob_tag in ["deep_woods", "wolves_den"]:
        for room in search_tag(mob_tag, category="mob_area"):
            if room.id in deleted_ids:
                continue
            if _is_system_room(room):
                continue
            _return_fungibles_to_reserve(room)
            deleted_ids.add(room.id)
            room.delete()
            room_count += 1

    print(f"  Deleted {room_count} room(s).")

    print("\n=== SOFT RESET COMPLETE ===\n")


def soft_rebuild():
    """Wipe the test world and rebuild it from scratch."""
    soft_reset()
    print("=== REBUILDING TEST WORLD ===\n")
    build_test_world()
    print("\n=== REBUILD COMPLETE ===")
