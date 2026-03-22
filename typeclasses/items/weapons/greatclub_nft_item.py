"""
GreatclubNFTItem — two-handed club with heavy stagger mastery.

Greatclubs are massive two-handed bludgeoning weapons. Their heavy
stagger mechanic is stronger than the one-handed club: higher proc
chance, bigger hit penalty, and longer duration at high mastery.
No extra attacks — greatclubs are slow and devastating.

Mastery progression:
    UNSKILLED: -2 hit, no stagger
    BASIC:      0 hit, no stagger
    SKILLED:   +2 hit, 15% stagger (-3 hit, 1 rnd)
    EXPERT:    +4 hit, 20% stagger (-3 hit, 1 rnd)
    MASTER:    +6 hit, 25% stagger (-4 hit, 2 rnds)
    GM:        +8 hit, 30% stagger (-4 hit, 2 rnds)

Stagger mechanic:
    On hit → roll d100 vs mastery-scaled chance.
    Success → apply STAGGERED named effect (hit penalty debuff).
    Stronger than club: higher chance, bigger penalty, longer at MASTER+.
    Anti-stacking: can't re-stagger already staggered targets.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

# Heavy stagger table: (chance %, hit penalty, duration in rounds)
_GREATCLUB_STAGGER = {
    MasteryLevel.UNSKILLED: (0, 0, 0),
    MasteryLevel.BASIC: (0, 0, 0),
    MasteryLevel.SKILLED: (15, -3, 1),
    MasteryLevel.EXPERT: (20, -3, 1),
    MasteryLevel.MASTER: (25, -4, 2),
    MasteryLevel.GRANDMASTER: (30, -4, 2),
}


class GreatclubNFTItem(WeaponNFTItem):
    """
    Greatclub weapons — melee, two-handed, bludgeoning, heavy stagger mastery.
    """

    weapon_type_key = "greatclub"
    two_handed = AttributeProperty(True)
    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.THIEF,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("greatclub", category="weapon_type")

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
        """On-hit heavy stagger check — chance to debuff target's hit rolls."""
        self._try_stagger(wielder, target)
        return damage

    def _try_stagger(self, wielder, target):
        """
        Attempt to heavily stagger the target.

        Rolls d100 vs mastery-scaled chance. On success, applies
        STAGGERED named effect (hit penalty debuff). Stronger than
        the one-handed club variant.
        Anti-stacking: skips if target already staggered.
        """
        mastery = self.get_wielder_mastery(wielder)
        chance, penalty, duration = _GREATCLUB_STAGGER.get(mastery, (0, 0, 0))
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
            f"|r*STAGGER* Your greatclub sends {target.key} reeling! "
            f"({penalty} hit, {duration} rnd)|n"
        )
        target.msg(
            f"|r*STAGGER* {wielder.key}'s greatclub sends you reeling! "
            f"({penalty} hit, {duration} rnd)|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|r*STAGGER* {wielder.key}'s greatclub sends "
                f"{target.key} reeling!|n",
                exclude=[wielder, target],
            )
