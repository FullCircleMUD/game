"""
SpearNFTItem — spear-type weapons with reach counter mastery.

Spears are one-handed piercing weapons that excel at support play.
When an enemy hits an ally, the spear wielder counter-attacks from
reach — fighting from behind the front line.

Mastery progression:
    UNSKILLED: -2 hit, no reach counters
    BASIC:      0 hit, no reach counters
    SKILLED:   +2 hit, 1 reach counter/round
    EXPERT:    +4 hit, 1 reach counter/round
    MASTER:    +6 hit, 2 reach counters/round
    GM:        +8 hit, 3 reach counters/round

Reach counter mechanic:
    When an enemy hits an ally of the spear wielder (same combat),
    the spear wielder gets a free counter-attack against that enemy.
    Counter-attacks cannot be parried and do not cascade.
    Tracked per-round via combat handler's reach_counters_remaining.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Reach counter-attacks per round by mastery
_SPEAR_REACH_COUNTERS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 3,
}


class SpearNFTItem(WeaponNFTItem):
    """
    Spear weapons — melee, one-handed, reach counter mastery path.
    """

    weapon_type_key = "spear"
    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("spear", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_reach_counters_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SPEAR_REACH_COUNTERS.get(mastery, 0)
