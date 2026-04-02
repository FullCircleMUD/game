"""
NinjatoNFTItem — ninjato-type weapons.

NinjatoMixin defines all mastery tables and overrides — shared by
both NinjatoNFTItem (player weapons) and MobNinjato (mob weapons).

A straight-bladed ninja sword. Two-handed finesse weapon — the ninja's
signature blade. Combines extra attacks, parries, and at GM mastery,
parry advantage and riposte.

Mastery progression:
    UNSKILLED: -2 hit, 1 attack, 0 parries
    BASIC:      0 hit, 1 attack, 0 parries
    SKILLED:   +2 hit, 1 attack, 1 parry
    EXPERT:    +4 hit, 2 attacks, 1 parry
    MASTER:    +6 hit, 2 attacks, 2 parries
    GM:        +8 hit, 2 attacks, 2 parries (parry advantage, riposte)

Two-handed, finesse, no dual-wield. Ninja only.
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

_NINJATO_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 2,
}


class NinjatoMixin:
    """Ninjato weapon identity — mastery tables and overrides.

    Shared by NinjatoNFTItem and MobNinjato. Single source of truth
    for ninjato combat mechanics.
    """

    weapon_type_key = "ninjato"
    is_finesse = AttributeProperty(True)
    two_handed = AttributeProperty(True)
    can_dual_wield = AttributeProperty(False)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NINJATO_EXTRA_ATTACKS.get(mastery, 0)

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NINJATO_PARRIES.get(mastery, 0)

    def get_parry_advantage(self, wielder):
        """Parry advantage at GM only."""
        mastery = self.get_wielder_mastery(wielder)
        return mastery == MasteryLevel.GRANDMASTER

    def has_riposte(self, wielder):
        """Riposte at GM only."""
        mastery = self.get_wielder_mastery(wielder)
        return mastery == MasteryLevel.GRANDMASTER


class NinjatoNFTItem(NinjatoMixin, WeaponNFTItem):
    """
    Ninjato weapons — two-handed finesse melee, extra attacks + parries.

    Balanced offense/defense: extra attacks at EXPERT+, parries scaling
    to 2 at MASTER+, parry advantage and riposte at GM. Ninja only.
    """

    required_classes = AttributeProperty([CharacterClass.NINJA])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("ninjato", category="weapon_type")
