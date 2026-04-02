"""
DaggerNFTItem — dagger-type weapons.

Daggers are fast, light finesse weapons. Their mastery path focuses
on speed (extra attacks) and precision (lower crit threshold).
At MASTER+, daggers gain off-hand attacks when dual-wielding.

Mastery progression:
    UNSKILLED: -2 hit, 0 extra attacks, no crit bonus, 0 off-hand
    BASIC:      0 hit, 0 extra attacks, no crit bonus, 0 off-hand
    SKILLED:   +2 hit, +1 extra attack, no crit bonus, 0 off-hand
    EXPERT:    +4 hit, +1 extra attack, crit on 19+ (-1), 0 off-hand
    MASTER:    +6 hit, +1 extra attack, crit on 19+ (-1), 1 off-hand
    GM:        +8 hit, +1 extra attack, crit on 18+ (-2), 1 off-hand

DaggerMixin defines all mastery tables and overrides — shared by
both DaggerNFTItem (player weapons) and MobDagger (mob weapons).
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

_DAGGER_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

_DAGGER_OFFHAND_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

_DAGGER_CRIT_MODIFIER = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: -1,
    MasteryLevel.MASTER: -1,
    MasteryLevel.GRANDMASTER: -2,
}


class DaggerMixin:
    """Dagger weapon identity — mastery tables and overrides.

    Shared by DaggerNFTItem and MobDagger. Single source of truth
    for dagger combat mechanics.
    """

    weapon_type_key = "dagger"
    is_finesse = AttributeProperty(True)
    can_dual_wield = AttributeProperty(True)

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _DAGGER_EXTRA_ATTACKS.get(mastery, 0)

    def get_mastery_crit_threshold_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _DAGGER_CRIT_MODIFIER.get(mastery, 0)

    def get_offhand_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _DAGGER_OFFHAND_ATTACKS.get(mastery, 0)


class DaggerNFTItem(DaggerMixin, WeaponNFTItem):
    """
    Dagger weapons — melee, finesse, speed + crit focused mastery path.
    """

    excluded_classes = AttributeProperty([CharacterClass.CLERIC])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("dagger", category="weapon_type")
