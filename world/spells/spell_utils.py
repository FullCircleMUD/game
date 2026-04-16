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


# ── Actor target resolution (for spells targeting characters/mobs) ───


def resolve_actor_target(caster, target_str, target_type):
    """Resolve an actor target for a spell.

    Used by ``cmd_cast`` and ``cmd_zap`` when the spell's ``target_type``
    is ``"hostile"``, ``"friendly"``, or ``"any_actor"``. Returns the resolved
    actor or ``None``; on ``None`` an error message has already been
    sent to the caster so callers just ``return``.

    Scoping:
        - Search is scoped to living actors in ``caster.location``
          (same room as the caster). No fallback to the room itself,
          no cross-room lookup.
        - A "living actor" is an object with an ``hp`` attribute and
          ``hp > 0``. This filters out rooms, items, fixtures, corpses,
          and dead mobs — the exact failure mode that caused the
          ``cast drain life bee-1`` crash.
        - Honours ``key-N`` numeric disambiguation via ``caller.search``.
          The user types ``bee-1`` to pick the first bee in a room full
          of bees.

    Per-target_type rules:
        - ``"hostile"`` — self is rejected (you can't cast a hostile
          spell on yourself via this path). Empty ``target_str`` is an
          error (no default target for hostile spells).
        - ``"friendly"`` — self is allowed. Empty ``target_str`` defaults
          to self.
        - ``"any_actor"`` — self is rejected (same as hostile — use
          ``score`` to check your own stats). Empty ``target_str`` is
          an error.

    Args:
        caster: The spell caster.
        target_str: Target name typed by the player (raw; stripped here).
        target_type: One of ``"hostile"``, ``"friendly"``, ``"any_actor"``.

    Returns:
        The resolved actor, or ``None``. Error message already sent
        on ``None``.
    """
    target_str = (target_str or "").strip()

    # Friendly defaults to self when no target is given
    if not target_str:
        if target_type == "friendly":
            return caster
        caster.msg("You need to specify a target.")
        return None

    if target_type not in ("hostile", "friendly", "any_actor"):
        caster.msg(f"Unknown actor target type '{target_type}'.")
        return None

    if not caster.location:
        caster.msg("You aren't anywhere where you could target that.")
        return None

    # ── Hostile / any_actor: delegate to attack priority resolvers ──
    # Both use hostile priority (enemy > bystander > ally > self in
    # combat, stranger > groupmate > self out of combat). Self is
    # rejected for both — hostile spells can't self-target, and
    # any_actor spells (augur, identify_creature) have no reason to
    # self-target when score/prompt are free. walk_contents inside
    # the priority helpers never includes the room object, so the
    # bee-tree crash is structurally impossible on this path.
    if target_type in ("hostile", "any_actor"):
        if caster.scripts.get("combat_handler"):
            target = resolve_attack_target_in_combat(caster, target_str)
        else:
            target = resolve_attack_target_out_of_combat(caster, target_str)

        if target is None:
            caster.msg(f"There's no '{target_str}' here.")
            return None

        # Self reached only via the self-bucket fallback in the
        # priority helpers, or via _is_self_keyword interception
        # when the player typed "me" / "self". Both hostile and
        # any_actor reject self-targeting.
        if target is caster:
            caster.msg("You can't target yourself with that spell.")
            return None

        return target

    # ── Friendly: delegate to friendly priority resolvers ──
    # Friendly priority (self > ally/groupmate > bystander/stranger >
    # enemy). "cast cure light goblin" prefers an allied goblin over
    # an enemy goblin; enemy still wins when it's the only name match.
    # Hidden actors are filtered via walk_contents inside the priority
    # resolvers. me / self keywords return caster directly — friendly
    # spells allow self. (Empty target_str for friendly is already
    # handled above — defaults to caster.)
    if caster.scripts.get("combat_handler"):
        target = resolve_friendly_target_in_combat(caster, target_str)
    else:
        target = resolve_friendly_target_out_of_combat(caster, target_str)

    if target is None:
        caster.msg(f"There's no '{target_str}' here.")
        return None

    return target


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
        # Inventory first — players most often identify items they
        # just picked up ("what does this new loot do?"). Worn items
        # excluded via exclude_worn — remove it first to identify.
        # Falls through to room if nothing in inventory matches.
        target = resolve_item_in_source(
            caster, caster, target_str, quiet=True, exclude_worn=True,
        )
        if isinstance(target, list):
            target = target[0] if target else None
        if target is not None:
            return target
        # Fall through to room
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
