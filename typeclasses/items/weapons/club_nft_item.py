"""
ClubNFTItem — club-type weapons with stagger mastery.

Clubs are simple one-handed bludgeoning weapons. Their stagger mechanic
applies a hit penalty debuff to the target, representing being thrown
off-balance by a heavy blow. At high mastery, clubs gain extra attacks.

Mastery progression:
    UNSKILLED: -2 hit, no stagger, 0 extra attacks
    BASIC:      0 hit, no stagger, 0 extra attacks
    SKILLED:   +2 hit, 10% stagger (-2 hit, 1 rnd), 0 extra attacks
    EXPERT:    +4 hit, 15% stagger (-2 hit, 1 rnd), 0 extra attacks
    MASTER:    +6 hit, 15% stagger (-2 hit, 1 rnd), 1 extra attack
    GM:        +8 hit, 20% stagger (-2 hit, 1 rnd), 1 extra attack

Stagger mechanic:
    On hit → roll d100 vs mastery-scaled chance.
    Success → apply STAGGERED named effect (hit penalty debuff).
    Anti-stacking: can't re-stagger already staggered targets.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Stagger table: (chance %, hit penalty, duration in rounds)
_CLUB_STAGGER = {
    MasteryLevel.UNSKILLED: (0, 0, 0),
    MasteryLevel.BASIC: (0, 0, 0),
    MasteryLevel.SKILLED: (10, -2, 1),
    MasteryLevel.EXPERT: (15, -2, 1),
    MasteryLevel.MASTER: (15, -2, 1),
    MasteryLevel.GRANDMASTER: (20, -2, 1),
}

# Extra attacks by mastery
_CLUB_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}


class ClubNFTItem(WeaponNFTItem):
    """
    Club weapons — melee, bludgeoning, light stagger mastery.
    """

    weapon_type_key = "club"
    excluded_classes = AttributeProperty([CharacterClass.MAGE])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("club", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _CLUB_EXTRA_ATTACKS.get(mastery, 0)

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """On-hit stagger check — chance to debuff target's hit rolls."""
        self._try_stagger(wielder, target)
        return damage

    def _try_stagger(self, wielder, target):
        """
        Attempt to stagger the target with a crushing blow.

        Rolls d100 vs mastery-scaled chance. On success, applies
        STAGGERED named effect (hit penalty debuff for 1 round).
        Anti-stacking: skips if target already staggered.
        """
        mastery = self.get_wielder_mastery(wielder)
        chance, penalty, duration = _CLUB_STAGGER.get(mastery, (0, 0, 0))
        if chance <= 0:
            return

        # Anti-stacking
        if hasattr(target, "has_effect") and target.has_effect("staggered"):
            return

        roll = dice.roll("1d100")
        if roll > chance:
            return

        target.apply_staggered(penalty, duration, source=wielder)

        wielder.msg(
            f"|r*STAGGER* Your club sends {target.key} reeling! "
            f"({penalty} hit, {duration} rnd)|n"
        )
        target.msg(
            f"|r*STAGGER* {wielder.key}'s club sends you reeling! "
            f"({penalty} hit, {duration} rnd)|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|r*STAGGER* {wielder.key}'s club sends "
                f"{target.key} reeling!|n",
                exclude=[wielder, target],
            )
