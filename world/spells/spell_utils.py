"""
Spell utility helpers — damage application and AoE targeting.

apply_spell_damage() is a thin wrapper around BaseActor.take_damage()
that accepts a DamageType enum (converting to string internally).
All damage-dealing spells should use this for consistency.

get_room_enemies() and get_room_all() provide AoE targeting helpers.
"""

from enums.damage_type import DamageType


def apply_spell_damage(target, raw_damage, damage_type):
    """
    Apply spell damage to target via the central take_damage() pipeline.

    Args:
        target: The entity taking damage.
        raw_damage: Pre-resistance damage amount.
        damage_type: DamageType enum member.

    Returns:
        int: Actual damage dealt after resistance.
    """
    return target.take_damage(
        raw_damage, damage_type=damage_type.value, cause="spell"
    )


def get_room_enemies(caster):
    """
    Get all living enemies in the caster's room.

    Uses combat_utils.get_sides() if the caster is in combat,
    otherwise falls back to finding all NPCs in the room.

    Returns:
        list: Enemy entities in the room.
    """
    room = caster.location
    if not room:
        return []

    # If in combat, use the combat system's side detection
    handler = caster.scripts.get("combat_handler")
    if handler:
        from combat.combat_utils import get_sides
        _allies, enemies = get_sides(caster)
        return enemies

    # Out of combat: find all living NPCs in the room
    from typeclasses.actors.character import FCMCharacter
    enemies = []
    for obj in room.contents:
        if obj == caster:
            continue
        if getattr(obj, "hp", None) is not None and obj.hp > 0:
            if not isinstance(obj, FCMCharacter):
                enemies.append(obj)
    return enemies


def get_room_all(caster):
    """
    Get all living entities in the room, including the caster.

    Used by unsafe AoE spells (Fireball) that hit everything.

    Returns:
        list: All living entities in the room.
    """
    room = caster.location
    if not room:
        return []

    return [
        obj for obj in room.contents
        if getattr(obj, "hp", None) is not None and obj.hp > 0
    ]


def get_room_enemies_at_height(caster):
    """
    Get living enemies at the same vertical height as the caster.

    Wraps get_room_enemies() with a room_vertical_position filter.
    Useful for AoE spells that only affect targets at the same height.

    Returns:
        list: Enemy entities at the caster's height.
    """
    caster_height = getattr(caster, "room_vertical_position", 0)
    return [
        e for e in get_room_enemies(caster)
        if getattr(e, "room_vertical_position", 0) == caster_height
    ]


def get_room_all_at_height(caster):
    """
    Get all living entities at the same vertical height as the caster.

    Wraps get_room_all() with a room_vertical_position filter.
    Useful for unsafe AoE spells that only affect targets at the same height.

    Returns:
        list: All living entities at the caster's height.
    """
    caster_height = getattr(caster, "room_vertical_position", 0)
    return [
        e for e in get_room_all(caster)
        if getattr(e, "room_vertical_position", 0) == caster_height
    ]


# ── Item target resolution (for spells with target_type=*_item) ───────


def resolve_item_target(caster, target_str, target_type):
    """Resolve an item target for a spell.

    Used by ``cmd_cast`` and ``cmd_zap`` when the spell's ``target_type``
    is ``"inventory_item"``, ``"world_item"``, or ``"any_item"``.

    Visibility:
        - ``inventory_item`` candidates are everything in
          ``caster.contents`` that is not the caster itself. Carried
          items are always visible to their owner; no hidden/invisible
          filtering is applied. (If a future "carried but hidden" item
          type appears, this needs revisiting.)
        - ``world_item`` candidates are objects in the caster's
          location and exits in the room, filtered by the existing
          ``utils.find_exit_target`` helper which respects
          ``HiddenObjectMixin`` and ``InvisibleObjectMixin``.
        - ``any_item`` tries ``world_item`` first, then falls through
          to ``inventory_item``.

    Args:
        caster: The spell caster.
        target_str: The target name typed by the player (raw, not
            stripped — the helper handles whitespace).
        target_type: One of ``"inventory_item"``, ``"world_item"``,
            ``"any_item"``.

    Returns:
        The resolved object, or ``None``. On ``None`` an error message
        has already been sent to the caster, so callers should simply
        return without doing further work.
    """
    target_str = (target_str or "").strip()
    if not target_str:
        caster.msg("You need to specify a target.")
        return None

    if target_type == "inventory_item":
        return _resolve_inventory_item(caster, target_str)

    if target_type == "world_item":
        return _resolve_world_item(caster, target_str)

    if target_type == "any_item":
        # Try the room first — a door called "iron door" should resolve
        # to the door, not to a carried item with the same name.
        target = _resolve_world_item(caster, target_str, silent=True)
        if target is not None:
            return target
        return _resolve_inventory_item(caster, target_str)

    # Caller passed an unknown type. Defensive — should not happen.
    caster.msg(f"Unknown item target type '{target_type}'.")
    return None


def _resolve_inventory_item(caster, target_str):
    """Find an item in the caster's own contents by name."""
    candidates = [obj for obj in caster.contents if obj is not caster]
    if not candidates:
        caster.msg(f"You aren't carrying anything called '{target_str}'.")
        return None

    target = caster.search(
        target_str,
        candidates=candidates,
        quiet=True,
    )
    if isinstance(target, list):
        target = target[0] if target else None
    if not target:
        caster.msg(f"You aren't carrying anything called '{target_str}'.")
        return None
    return target


def _resolve_world_item(caster, target_str, silent=False):
    """Find an object or exit in the caster's room by name.

    When ``silent`` is True, suppresses the not-found message — used
    by the ``any_item`` fall-through so we don't double-report.
    """
    if not caster.location:
        if not silent:
            caster.msg("You aren't anywhere where you could target that.")
        return None

    # find_exit_target sends its own "you don't see X" message on miss.
    # Suppress it when we're inside the any_item fall-through path.
    if silent:
        # Inline a quieter version of the lookup so we don't print noise.
        return _find_world_item_quiet(caster, target_str)

    from utils.find_exit_target import find_exit_target
    return find_exit_target(caster, target_str)


def _find_world_item_quiet(caster, target_str):
    """Quiet version of find_exit_target — no error messages.

    Mirrors the lookup logic but returns None silently on miss so the
    any_item path can fall through to inventory.
    """
    from utils.find_exit_target import _is_visible

    target = caster.search(
        target_str,
        location=caster.location,
        quiet=True,
    )
    if target:
        if isinstance(target, list):
            target = target[0]
        if _is_visible(target, caster):
            return target

    name_lower = target_str.lower()
    for ex in caster.location.exits:
        if not _is_visible(ex, caster):
            continue
        if name_lower in ex.key.lower():
            return ex
        if name_lower in [a.lower() for a in ex.aliases.all()]:
            return ex

    return None
