"""
SpearNFTItem — spear-type weapons with reach counter mastery.

SpearMixin defines all mastery tables and overrides — shared by
both SpearNFTItem (player weapons) and MobSpear (mob weapons).

Spears are two-handed piercing weapons that excel at party support play.
When an enemy hits an ally, the spear wielder counter-attacks from
reach — fighting from behind the front line. Two-handed: no shield,
no parries — the spear wielder relies on the tank for protection.

Mastery progression (alternating crit / counter unlocks):
    UNSKILLED: -2 hit, no counters, no crit bonus
    BASIC:      0 hit, no counters, no crit bonus
    SKILLED:   +2 hit, no counters, crit on 19+ (-1)
    EXPERT:    +4 hit, 1 reach counter/round, crit on 19+
    MASTER:    +6 hit, 1 reach counter/round, crit on 18+ (-2)
    GM:        +8 hit, 2 reach counters/round, crit on 18+

Reach counter mechanic:
    When an enemy hits an ally of the spear wielder (same combat),
    the spear wielder gets a free counter-attack against that enemy.
    Counter-attacks cannot be parried and do not cascade.
    Tracked per-round via combat handler's reach_counters_remaining.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Reach counter-attacks per round by mastery
_SPEAR_REACH_COUNTERS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

# Crit threshold modifier by mastery
_SPEAR_CRIT_MODIFIER = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: -1,
    MasteryLevel.EXPERT: -1,
    MasteryLevel.MASTER: -2,
    MasteryLevel.GRANDMASTER: -2,
}


class SpearMixin:
    """Spear weapon identity — mastery tables and overrides.

    Shared by SpearNFTItem and MobSpear. Single source of truth
    for spear combat mechanics.
    """

    weapon_type_key = "spear"
    base_damage = AttributeProperty("d8")
    damage_type = AttributeProperty(DamageType.PIERCING)
    weight = AttributeProperty(3.0)
    two_handed = AttributeProperty(True)

    def get_parries_per_round(self, wielder):
        return 0

    def get_reach_counters_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SPEAR_REACH_COUNTERS.get(mastery, 0)

    def get_mastery_crit_threshold_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SPEAR_CRIT_MODIFIER.get(mastery, 0)


class SpearNFTItem(SpearMixin, WeaponNFTItem):
    """
    Spear weapons — melee, two-handed, reach counter + crit mastery path.
    """

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("spear", category="weapon_type")
