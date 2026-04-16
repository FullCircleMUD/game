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


