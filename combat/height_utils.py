"""
Height-aware combat helpers.

Determines whether an attacker can reach a target based on vertical
position and weapon type, and applies hit modifiers for ranged weapons
used at close quarters.
"""


def can_reach_target(attacker, target, weapon):
    """
    Can this attack reach the target given their heights?

    Melee/unarmed require same room_vertical_position.
    Missile weapons (wielded or innate) can hit across heights.
    """
    if attacker.room_vertical_position == target.room_vertical_position:
        return True
    # Different heights — wielded missile weapon
    if weapon and getattr(weapon, "weapon_type", "melee") == "missile":
        return True
    # Innate ranged (dragon breath, venom spit) via InnateRangedMixin
    mob_weapon_type = getattr(attacker, "mob_weapon_type", None)
    if mob_weapon_type == "missile":
        innate_range = getattr(attacker, "innate_ranged_range", 0)
        if innate_range <= 0:
            return True  # unlimited range within room
        height_diff = abs(
            attacker.room_vertical_position - target.room_vertical_position
        )
        return height_diff <= innate_range
    return False


def get_height_hit_modifier(attacker, target, weapon):
    """
    Return a hit modifier based on relative heights and weapon type.

    Missile weapons (wielded or innate) at the same height as the target
    suffer -4 to hit (drawing/aiming in melee range is dangerous).
    At different heights there is no penalty.
    """
    is_ranged = False
    if weapon and getattr(weapon, "weapon_type", "melee") == "missile":
        is_ranged = True
    elif getattr(attacker, "mob_weapon_type", None) == "missile":
        is_ranged = True

    if not is_ranged:
        return 0  # melee — no modifier

    if attacker.room_vertical_position == target.room_vertical_position:
        return -4  # ranged in melee range
    return 0  # ranged at distance — no penalty
