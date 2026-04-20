"""
InnateRangedMixin — innate ranged attack capability for non-humanoid mobs.

Three-tier weapon model:
  1. Humanoid mobs wield weapon objects (bow, crossbow) → HumanoidWearslotsMixin
  2. Non-humanoid mobs default to melee (bite, claw) → no mixin needed
  3. Non-humanoid mobs with innate ranged (dragon breath, venom spit) → this mixin

Sets mob_weapon_type = "ranged" so height_utils.can_reach_target() allows
cross-height attacks. Combined with FlyingMixin, enables attack from the
air without descending.

Usage:
    class Dragon(InnateRangedMixin, FlyingMixin, AggressiveMob):
        innate_ranged_message = AttributeProperty("breathes fire at")
        damage_dice = AttributeProperty("3d8")
"""

from evennia.typeclasses.attributes import AttributeProperty


class InnateRangedMixin:
    """Mixin providing innate ranged attack for non-humanoid mobs."""

    # Flag checked by height_utils.can_reach_target()
    mob_weapon_type = AttributeProperty("ranged")

    # Flavor text for attack messages (e.g. "breathes fire at", "spits venom at")
    innate_ranged_message = AttributeProperty("attacks")

    # Max height differential for ranged attack (0 = unlimited within room)
    innate_ranged_range = AttributeProperty(0)
