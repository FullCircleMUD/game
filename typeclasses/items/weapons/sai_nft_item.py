"""
SaiNFTItem — sai-type weapons.

SaiMixin defines all mastery tables and overrides — shared by
both SaiNFTItem (player weapons) and MobSai (mob weapons).

A pronged defensive weapon. Pure parry specialist — the highest parry
count of any one-handed weapon. Disarm triggers on successful parry
(parry-to-disarm mechanic to be implemented separately).

Mastery progression:
    UNSKILLED: -2 hit, 1 attack, 0 parries
    BASIC:      0 hit, 1 attack, 1 parry
    SKILLED:   +2 hit, 1 attack, 2 parries
    EXPERT:    +4 hit, 1 attack, 3 parries
    MASTER:    +6 hit, 1 attack, 4 parries
    GM:        +8 hit, 1 attack, 5 parries

No extra attacks, no off-hand, no parry advantage, no riposte.
Dual-wieldable. Ninja only.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

_SAI_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 1,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 3,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 5,
}


class SaiMixin:
    """Sai weapon identity — mastery tables and overrides.

    Shared by SaiNFTItem and MobSai. Single source of truth
    for sai combat mechanics.
    """

    weapon_type_key = "sai"
    can_dual_wield = AttributeProperty(True)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_PARRIES.get(mastery, 0)

    def get_extra_attacks(self, wielder):
        return 0


class SaiNFTItem(SaiMixin, WeaponNFTItem):
    """
    Sai weapons — one-handed melee, pure parry specialist.

    Highest parry count of any one-handed weapon (up to 5 at GM).
    No extra attacks, no off-hand attacks, no parry advantage, no riposte.
    Disarm will trigger on successful parry (separate mechanic). Ninja only.
    """

    required_classes = AttributeProperty([CharacterClass.NINJA])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("sai", category="weapon_type")
