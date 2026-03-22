"""
SlingNFTItem — sling-type missile weapons with concussive daze mastery.

Slings are the everyman's ranged weapon — no class restrictions, usable
by anyone. A well-placed stone to the skull can daze opponents, denying
them their next action. Simple, reliable, and effective.

Mastery progression:
    UNSKILLED: -2 hit, no daze, 0 extra attacks
    BASIC:      0 hit, no daze, 0 extra attacks
    SKILLED:   +2 hit, 10% daze (1 round stun), 0 extra attacks
    EXPERT:    +4 hit, 15% daze (1 round stun), 0 extra attacks
    MASTER:    +6 hit, 20% daze (1 round stun), 0 extra attacks
    GM:        +8 hit, 25% daze (1 round stun), 0 extra attacks

Daze mechanic:
    On hit → roll d100 vs mastery-scaled chance.
    Success → target STUNNED for 1 round (action denial, no advantage).
    HUGE+ targets are immune (stone to a giant does nothing).
    Anti-stacking: can't re-stun already stunned target.
"""

from evennia.typeclasses.attributes import AttributeProperty

from combat.combat_utils import get_actor_size
from enums.actor_size import ActorSize
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Daze chance % by mastery
_SLING_DAZE = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 10,
    MasteryLevel.EXPERT: 15,
    MasteryLevel.MASTER: 20,
    MasteryLevel.GRANDMASTER: 25,
}

# Sizes immune to daze
_DAZE_IMMUNE_SIZES = {ActorSize.HUGE, ActorSize.GARGANTUAN}


class SlingNFTItem(WeaponNFTItem):
    """
    Sling weapons — missile, concussive daze mastery. No class restrictions.
    """

    weapon_type_key = "sling"
    weapon_type = AttributeProperty("missile")
    range = AttributeProperty(1)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("sling", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
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
        chance = _SLING_DAZE.get(mastery, 0)
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
        applied = target.apply_stunned(1, source=wielder)

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
