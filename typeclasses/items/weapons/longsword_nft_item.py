"""
LongswordNFTItem — longsword-type weapons.

Longswords are versatile one-handed blades. Their mastery path focuses
on parrying and balanced offense:

    UNSKILLED: -2 hit, no parry
    BASIC:      0 hit, no parry
    SKILLED:   +2 hit, 1 parry/round
    EXPERT:    +4 hit, 2 parries/round
    MASTER:    +4 hit, 2 parries/round, +1 extra attack/round
    GRANDMASTER: +5 hit, 3 parries/round, +1 extra attack, advantage on parries
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Custom hit bonuses — lower at MASTER/GM to offset extra attacks and parries
_LONGSWORD_HIT_BONUSES = {
    MasteryLevel.UNSKILLED: -2,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 4,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 5,
}

_LONGSWORD_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 2,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 3,
}

_LONGSWORD_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}


class LongswordMixin:
    """Longsword weapon identity — mastery tables and overrides.

    Shared by LongswordNFTItem and MobLongsword. Single source of truth
    for longsword combat mechanics.
    """

    weapon_type_key = "long_sword"

    def get_mastery_hit_bonus(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _LONGSWORD_HIT_BONUSES.get(mastery, 0)

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _LONGSWORD_PARRIES.get(mastery, 0)

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _LONGSWORD_EXTRA_ATTACKS.get(mastery, 0)

    def get_parry_advantage(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return mastery == MasteryLevel.GRANDMASTER


class LongswordNFTItem(LongswordMixin, WeaponNFTItem):
    """
    Longsword weapons — melee, parry-focused mastery path.
    """

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("long_sword", category="weapon_type")
