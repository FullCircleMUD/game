"""
Spell utility helpers — damage application and AoE targeting.

apply_spell_damage() is a thin wrapper around BaseActor.take_damage()
that accepts a DamageType enum (converting to string internally).
All damage-dealing spells should use this for consistency.

get_room_enemies() and get_room_all() provide AoE targeting helpers.
"""

from enums.damage_type import DamageType
from utils.targeting.helpers import (
    resolve_attack_target_in_combat,
    resolve_attack_target_out_of_combat,
    resolve_friendly_target_in_combat,
    resolve_friendly_target_out_of_combat,
    resolve_item_in_source,
)


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


# ── Spell target resolution ──────────────────────────────────────────


def resolve_spell_target(caster, target_str, target_type):
    """Resolve a spell target by ``target_type``.

    Single entry point for all spell target resolution, used by
    ``cmd_cast`` and ``cmd_zap``. Routes to the appropriate targeting
    primitive based on the spell's ``target_type``. Returns the
    resolved target or ``None``. On ``None``, an error message has
    already been sent to the caster — callers just ``return``.

    Target types:

        ``"self"``           — returns caster, no resolution needed.
        ``"none"``           — returns None, no resolution needed.
        ``"hostile"``        — attack-priority actor resolution
                               (enemy > bystander > ally > self),
                               self rejected.
        ``"any_actor"``      — same as hostile (attack priority,
                               self rejected).
        ``"friendly"``       — friendly-priority actor resolution
                               (self > ally > bystander > enemy),
                               self allowed, empty target defaults
                               to self.
        ``"inventory_item"`` — item in caster's inventory.
        ``"world_item"``     — item/exit in caster's room (via
                               ``find_exit_target``).
        ``"any_item"``       — inventory first (exclude worn),
                               room fallback.
    """
    # ── Self / none: no resolution ──
    if target_type == "self":
        return caster
    if target_type == "none":
        return None

    target_str = (target_str or "").strip()

    # Friendly defaults to self when no target is given
    if not target_str:
        if target_type == "friendly":
            return caster
        caster.msg("You need to specify a target.")
        return None

    if not caster.location and target_type != "inventory_item":
        caster.msg("You aren't anywhere where you could target that.")
        return None

    # ── Hostile / any_actor: attack-priority actor resolution ──
    if target_type in ("hostile", "any_actor"):
        if caster.scripts.get("combat_handler"):
            target = resolve_attack_target_in_combat(caster, target_str)
        else:
            target = resolve_attack_target_out_of_combat(caster, target_str)
        if target is None:
            caster.msg(f"There's no '{target_str}' here.")
            return None
        if target is caster:
            caster.msg("You can't target yourself with that spell.")
            return None
        return target

    # ── Friendly: friendly-priority actor resolution ──
    if target_type == "friendly":
        if caster.scripts.get("combat_handler"):
            target = resolve_friendly_target_in_combat(caster, target_str)
        else:
            target = resolve_friendly_target_out_of_combat(caster, target_str)
        if target is None:
            caster.msg(f"There's no '{target_str}' here.")
            return None
        return target

    # ── Inventory item ──
    if target_type == "inventory_item":
        return _resolve_inventory_item(caster, target_str)

    # ── World item ──
    if target_type == "world_item":
        return _resolve_world_item(caster, target_str)

    # ── Any item: inventory first, room fallback ──
    if target_type == "any_item":
        target = resolve_item_in_source(
            caster, caster, target_str, quiet=True, exclude_worn=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        if target is not None:
            return target
        if caster.location:
            target = resolve_item_in_source(
                caster, caster.location, target_str, quiet=True,
            )
            if isinstance(target, list):
                target = target[0] if target else None
            if target is not None:
                return target
        caster.msg(f"You don't see '{target_str}' here.")
        return None

    # Unknown type — defensive
    caster.msg(f"Unknown target type '{target_type}'.")
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
