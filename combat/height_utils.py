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
    Missile weapons can hit any height within the room.
    """
    if attacker.room_vertical_position == target.room_vertical_position:
        return True
    # Different heights — only missile weapons can reach
    if weapon and getattr(weapon, "weapon_type", "melee") == "missile":
        return True
    return False


def get_height_hit_modifier(attacker, target, weapon):
    """
    Return a hit modifier based on relative heights and weapon type.

    Missile weapons at the same height as the target suffer -4 to hit
    (drawing/aiming in melee range is dangerous). At different heights
    there is no penalty.
    """
    if not weapon or getattr(weapon, "weapon_type", "melee") != "missile":
        return 0  # melee at same height — no modifier
    if attacker.room_vertical_position == target.room_vertical_position:
        return -4  # ranged in melee range
    return 0  # ranged at distance — no penalty
