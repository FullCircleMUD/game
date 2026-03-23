"""
Soft-rebuild: wipe the game world and rebuild it WITHOUT touching
player accounts, characters, or their inventories.

Usage (from Evennia shell / @py):
    from world.game_world.soft_rebuild_game_world import soft_rebuild
    soft_rebuild()

Or just the cleanup half:
    from world.game_world.soft_rebuild_game_world import soft_reset
    soft_reset()
"""

from evennia import ObjectDB, search_tag

from world.game_world.build_game_world import build_game_world


# Zone tags used by the game world build scripts
GAME_ZONE_TAGS = [
    "millholm",
]

# System rooms that must NEVER be deleted
SYSTEM_KEYS = {"Limbo", "Purgatory", "nft_recycle_bin"}


def _get_limbo():
    """Return the Limbo room (Evennia's default room, always id=2)."""
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
    """Return any gold/resources on an object back to the vault reserve."""
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
    Delete all game-world objects while preserving:
      - Player accounts and characters
      - Items/gold/resources in character inventories or account banks
      - System rooms (Limbo, Purgatory, Cemetery, RecycleBin)
      - Global scripts
    """
    limbo = _get_limbo()
    print("=== GAME WORLD SOFT RESET ===\n")

    # ── 1. Evacuate players to Limbo ────────────────────────────────
    print("[1/5] Evacuating players to Limbo...")
    evacuated = 0
    for zone_tag in GAME_ZONE_TAGS:
        for room in search_tag(zone_tag, category="zone"):
            for obj in list(room.contents):
                if _is_player_character(obj):
                    obj.location = limbo
                    obj.msg(
                        "|y[System] The world shimmers and reforms around you.|n"
                    )
                    evacuated += 1
    print(f"  Moved {evacuated} player(s) to Limbo.")

    # ── 2. Delete mobs and NPCs in game world rooms ──────────────────
    print("[2/5] Deleting mobs and NPCs...")
    mob_count = 0
    for zone_tag in GAME_ZONE_TAGS:
        for room in search_tag(zone_tag, category="zone"):
            for obj in list(room.contents):
                if obj.is_typeclass(
                    "typeclasses.actors.mob", exact=False
                ) or obj.is_typeclass(
                    "typeclasses.actors.npc", exact=False
                ):
                    _return_fungibles_to_reserve(obj)
                    obj.delete()
                    mob_count += 1
    print(f"  Deleted {mob_count} mob(s)/NPC(s).")

    # ── 3. Delete orphaned items in game world rooms ─────────────────
    print("[3/5] Deleting orphaned items...")
    item_count = 0
    for zone_tag in GAME_ZONE_TAGS:
        for room in search_tag(zone_tag, category="zone"):
            for obj in list(room.contents):
                if not obj.pk:
                    continue
                if _is_player_character(obj):
                    continue
                if _is_system_room(obj):
                    continue
                _return_fungibles_to_reserve(obj)
                obj.delete()
                item_count += 1
    print(f"  Deleted {item_count} item(s).")

    # ── 4. Delete exits from game world rooms ────────────────────────
    print("[4/5] Deleting exits...")
    exit_count = 0
    for obj in list(
        ObjectDB.objects.filter(db_typeclass_path__contains="exits")
    ):
        if not obj.pk:
            continue
        if obj.location and _is_system_room(obj.location):
            continue
        # Only delete exits whose source is in a game world zone
        if obj.location and obj.location.tags.get(category="zone") in GAME_ZONE_TAGS:
            obj.delete()
            exit_count += 1
    print(f"  Deleted {exit_count} exit(s).")

    # ── 5. Delete game-world rooms ───────────────────────────────────
    print("[5/5] Deleting game-world rooms...")
    room_count = 0
    deleted_ids = set()
    for zone_tag in GAME_ZONE_TAGS:
        for room in search_tag(zone_tag, category="zone"):
            if room.id in deleted_ids:
                continue
            if _is_system_room(room):
                continue
            _return_fungibles_to_reserve(room)
            deleted_ids.add(room.id)
            room.delete()
            room_count += 1
    print(f"  Deleted {room_count} room(s).")

    print("\n=== GAME WORLD SOFT RESET COMPLETE ===\n")


def soft_rebuild():
    """Wipe the game world and rebuild it from scratch."""
    soft_reset()
    print("=== REBUILDING GAME WORLD ===\n")
    build_game_world()
    print("\n=== GAME WORLD REBUILD COMPLETE ===")
