"""
SlingNFTItem — sling-type missile weapons with concussive daze mastery.

Slings are the everyman's ranged weapon — no class restrictions, usable
by anyone. A well-placed stone to the skull can daze opponents, denying
them their next action. Simple, reliable, and effective.

Mastery progression:
    UNSKILLED: -2 hit, no daze
    BASIC:      0 hit, no daze
    SKILLED:   +2 hit, 10% daze (1 round stun)
    EXPERT:    +4 hit, 15% daze (1 round stun), +1 extra attack
    MASTER:    +6 hit, 20% daze (1 round stun), +1 extra attack
    GM:        +8 hit, 25% daze (2 rounds stun), +1 extra attack

Daze mechanic:
    On hit → roll d100 vs mastery-scaled chance.
    Success → target STUNNED (action denial, no advantage).
    HUGE+ targets are immune (stone to a giant does nothing).
    Anti-stacking: can't re-stun already stunned target.
    GM capstone: 2-round stun duration.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from combat.combat_utils import get_actor_size
from enums.size import Size
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Daze chance % by mastery
_SLING_DAZE = {
    MasteryLevel.UNSKILLED: (0, 0),
    MasteryLevel.BASIC: (0, 0),
    MasteryLevel.SKILLED: (10, 1),
    MasteryLevel.EXPERT: (15, 1),
    MasteryLevel.MASTER: (20, 1),
    MasteryLevel.GRANDMASTER: (25, 2),
}

# Sizes immune to daze
_DAZE_IMMUNE_SIZES = {Size.HUGE, Size.GARGANTUAN}


class SlingMixin:
    """Sling weapon identity — mastery tables and overrides.

    Shared by SlingNFTItem and MobSling. Single source of truth
    for sling combat mechanics (concussive daze).
    """

    weapon_type_key = "sling"
    base_damage = AttributeProperty("d6")
    speed = AttributeProperty(2)
    weight = AttributeProperty(0.3)
    weapon_type = AttributeProperty("ranged")
    range = AttributeProperty(1)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value >= MasteryLevel.EXPERT.value:
            return 1
        return 0

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """On-hit daze check — chance to stun target."""
        self._try_daze(wielder, target)
        return damage

    def _try_daze(self, wielder, target):
        """
        Attempt to daze the target with a concussive stone hit.

        Rolls d100 vs mastery-scaled chance. On success:
        1. Applies STUNNED named effect (1 round action denial)
        HUGE+ targets are immune. Already-stunned targets are skipped.
        """
        mastery = self.get_wielder_mastery(wielder)
        chance, duration = _SLING_DAZE.get(mastery, (0, 0))
        if chance <= 0:
            return

        # Size gate — HUGE+ immune
        target_size = get_actor_size(target)
        if target_size in _DAZE_IMMUNE_SIZES:
            return

        # Already stunned — skip
        if hasattr(target, "has_effect") and target.has_effect("stunned"):
            return

        roll = dice.roll("1d100")
        if roll > chance:
            return

        # Apply STUNNED
        applied = target.apply_stunned(duration, source=wielder)

        if applied:
            wielder.msg(
                f"|y*DAZE* Your sling stone cracks {target.key} in the skull!|n"
            )
            target.msg(
                f"|y*DAZE* {wielder.key}'s sling stone cracks you in the skull! "
                f"You see stars!|n"
            )
            if wielder.location:
                wielder.location.msg_contents(
                    f"|y*DAZE* {wielder.key}'s sling stone cracks "
                    f"{target.key} in the skull!|n",
                    exclude=[wielder, target],
                )


class SlingNFTItem(SlingMixin, WeaponNFTItem):
    """
    Sling weapons — missile, concussive daze mastery. No class restrictions.
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("sling", category="weapon_type")
