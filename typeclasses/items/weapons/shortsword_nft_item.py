"""
ShortswordNFTItem — shortsword-type weapons.

Shortswords are versatile dual-wield specialists. Their mastery path
focuses on off-hand attacks with reducing penalty and light parry.

Mastery progression:
    UNSKILLED: -2 hit, 0 parries, 0 off-hand attacks
    BASIC:      0 hit, 0 parries, 0 off-hand attacks
    SKILLED:   +2 hit, 1 parry, 0 off-hand attacks
    EXPERT:    +4 hit, 1 parry, 1 off-hand attack (-4 penalty)
    MASTER:    +6 hit, 1 parry, 1 off-hand attack (-2 penalty)
    GM:        +8 hit, 2 parries, 1 off-hand attack (no penalty)

Off-hand attacks only fire when a dual-wield weapon is held in the
HOLD slot. Main hand mastery drives all bonuses — off-hand weapon
mastery is ignored. Off-hand weapon's damage dice and enchantment
bonuses (wear_effects) still apply.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

_SHORTSWORD_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

_SHORTSWORD_OFFHAND_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

_SHORTSWORD_OFFHAND_PENALTY = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: -4,
    MasteryLevel.MASTER: -2,
    MasteryLevel.GRANDMASTER: 0,
}


class ShortswordNFTItem(WeaponNFTItem):
    """
    Shortsword weapons — melee, dual-wield specialist with light parry.
    """

    weapon_type_key = "shortsword"
    is_finesse = AttributeProperty(True)
    can_dual_wield = AttributeProperty(True)
    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("shortsword", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SHORTSWORD_PARRIES.get(mastery, 0)

    def get_extra_attacks(self, wielder):
        return 0

    def get_offhand_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SHORTSWORD_OFFHAND_ATTACKS.get(mastery, 0)

    def get_offhand_hit_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SHORTSWORD_OFFHAND_PENALTY.get(mastery, 0)
