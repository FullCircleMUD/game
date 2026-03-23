"""
Shared zone management utilities.

Provides a generic clean_zone() that removes all rooms and objects tagged to a
given zone key while preserving player characters, system rooms, and asset
reserves. Used by every zone's soft_deploy.py.

Usage:
    from world.game_world.zone_utils import clean_zone
    clean_zone("millholm")
"""

from evennia import ObjectDB, search_tag


SYSTEM_KEYS = {"Limbo", "Purgatory", "nft_recycle_bin"}


def _get_limbo():
    return ObjectDB.objects.get(id=2)


def _is_player_character(obj):
    return obj.is_typeclass("typeclasses.actors.character.FCMCharacter", exact=False)


def _is_system_room(obj):
    return obj.key in SYSTEM_KEYS


def _return_fungibles_to_reserve(obj):
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


def clean_zone(zone_key: str):
    """
    Remove all game-world objects tagged to zone_key while preserving:
      - Player accounts and characters
      - Items/gold/resources in character inventories or account banks
      - System rooms (Limbo, Purgatory, RecycleBin)
      - Global scripts

    Safe to call on a zone that has never been built — returns immediately if
    no rooms carry the zone tag.
    """
    limbo = _get_limbo()
    print(f"=== CLEANING ZONE: {zone_key} ===\n")

    zone_rooms = list(search_tag(zone_key, category="zone"))
    if not zone_rooms:
        print(f"  No rooms tagged '{zone_key}'. Nothing to clean.\n")
        return

    # ── 1. Evacuate players ──────────────────────────────────────────
    print("[1/5] Evacuating players to Limbo...")
    evacuated = 0
    for room in zone_rooms:
        for obj in list(room.contents):
            if _is_player_character(obj):
                obj.location = limbo
                obj.msg("|y[System] The world shimmers and reforms around you.|n")
                evacuated += 1
    print(f"  Moved {evacuated} player(s) to Limbo.")

    # ── 2. Delete mobs and NPCs ──────────────────────────────────────
    print("[2/5] Deleting mobs and NPCs...")
    mob_count = 0
    for room in zone_rooms:
        for obj in list(room.contents):
            if obj.is_typeclass(
                "typeclasses.actors.mob", exact=False
            ) or obj.is_typeclass("typeclasses.actors.npc", exact=False):
                _return_fungibles_to_reserve(obj)
                obj.delete()
                mob_count += 1
    print(f"  Deleted {mob_count} mob(s)/NPC(s).")

    # ── 3. Delete orphaned items ─────────────────────────────────────
    print("[3/5] Deleting orphaned items...")
    item_count = 0
    for room in zone_rooms:
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

    # ── 4. Delete exits ──────────────────────────────────────────────
    print("[4/5] Deleting exits...")
    exit_count = 0
    for obj in list(ObjectDB.objects.filter(db_typeclass_path__contains="exits")):
        if not obj.pk:
            continue
        if obj.location and _is_system_room(obj.location):
            continue
        if obj.location and obj.location.tags.get(category="zone") == zone_key:
            obj.delete()
            exit_count += 1
    print(f"  Deleted {exit_count} exit(s).")

    # ── 5. Delete rooms ──────────────────────────────────────────────
    print("[5/5] Deleting rooms...")
    room_count = 0
    deleted_ids = set()
    for room in zone_rooms:
        if room.id in deleted_ids:
            continue
        if _is_system_room(room):
            continue
        _return_fungibles_to_reserve(room)
        deleted_ids.add(room.id)
        room.delete()
        room_count += 1
    print(f"  Deleted {room_count} room(s).")

    print(f"\n=== ZONE '{zone_key}' CLEAN COMPLETE ===\n")
