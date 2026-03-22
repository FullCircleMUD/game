"""
NinjatoNFTItem — ninjatō-type weapons.

A straight-bladed ninja sword. The ninja's signature weapon — combines
speed, precision, and dual-wield capability. Pure offense, no parries.

Mastery progression:
    UNSKILLED: -2 hit, 0 extra attacks, no crit bonus, 0 off-hand
    BASIC:      0 hit, 0 extra attacks, no crit bonus, 0 off-hand
    SKILLED:   +2 hit, 0 extra attacks, no crit bonus, 1 off-hand (-4)
    EXPERT:    +4 hit, +1 extra attack, crit on 19+ (-1), 1 off-hand (-2)
    MASTER:    +6 hit, +1 extra attack, crit on 19+ (-1), 1 off-hand (0)
    GM:        +8 hit, +1 extra attack, crit on 18+ (-2), 2 off-hand (0)

At GM dual-wielding: 1 base + 1 extra + 2 offhand = 4 attacks with crit
on 18+. The highest attack count of any weapon — justified by being
ninja-exclusive (prestige class earned through remorts).
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

_NINJATO_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

_NINJATO_CRIT_MODIFIER = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: -1,
    MasteryLevel.MASTER: -1,
    MasteryLevel.GRANDMASTER: -2,
}

_NINJATO_OFFHAND_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

_NINJATO_OFFHAND_PENALTY = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: -4,
    MasteryLevel.EXPERT: -2,
    MasteryLevel.MASTER: 0,
    MasteryLevel.GRANDMASTER: 0,
}


class NinjatoNFTItem(WeaponNFTItem):
    """
    Ninjatō weapons — one-handed finesse melee, speed + crit + dual-wield.

    Pure offense: extra attacks, crit threshold scaling, off-hand attacks.
    No parries, no defensive hooks. Ninja only.
    """

    weapon_type_key = "ninjato"
    is_finesse = AttributeProperty(True)
    can_dual_wield = AttributeProperty(True)
    required_classes = AttributeProperty([CharacterClass.NINJA])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("ninjato", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NINJATO_EXTRA_ATTACKS.get(mastery, 0)

    def get_mastery_crit_threshold_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NINJATO_CRIT_MODIFIER.get(mastery, 0)

    def get_offhand_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NINJATO_OFFHAND_ATTACKS.get(mastery, 0)

    def get_offhand_hit_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NINJATO_OFFHAND_PENALTY.get(mastery, 0)
