"""
RapierNFTItem — rapier-type weapons.

Rapiers are fast, precise thrusting blades that favour dexterity.
Finesse: uses max(STR, DEX) for hit and damage rolls.

Mastery path focuses on parrying and riposte (counter-attack on
successful parry). Contrasts with longsword's extra-attack path:

    UNSKILLED: -2 hit, no parry
    BASIC:      0 hit, no parry
    SKILLED:   +2 hit, 1 parry/round (no riposte yet)
    EXPERT:    +3 hit, 1 parry/round + riposte on successful parry
    MASTER:    +4 hit, 2 parries/round + riposte
    GRANDMASTER: +5 hit, 3 parries/round + riposte, advantage on parries
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from enums.size import Size
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Custom hit bonuses — lower at EXPERT+ to offset riposte attacks
_RAPIER_HIT_BONUSES = {
    MasteryLevel.UNSKILLED: -2,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 3,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 5,
}

_RAPIER_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 3,
}


class RapierMixin:
    """Rapier weapon identity — mastery tables and overrides.

    Shared by RapierNFTItem and MobRapier. Single source of truth
    for rapier combat mechanics.
    """

    weapon_type_key = "rapier"
    base_damage = AttributeProperty("d8")
    damage_type = AttributeProperty(DamageType.PIERCING)
    weight = AttributeProperty(1.5)
    is_finesse = AttributeProperty(True)

    def get_mastery_hit_bonus(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _RAPIER_HIT_BONUSES.get(mastery, 0)

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _RAPIER_PARRIES.get(mastery, 0)

    def has_riposte(self, wielder):
        """Riposte unlocks at EXPERT mastery."""
        mastery = self.get_wielder_mastery(wielder)
        return mastery.value >= MasteryLevel.EXPERT.value

    def get_parry_advantage(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return mastery == MasteryLevel.GRANDMASTER


class RapierNFTItem(RapierMixin, WeaponNFTItem):
    """
    Rapier weapons — melee, one-handed, finesse, riposte-focused mastery path.
    """

    size = AttributeProperty(Size.SMALL.value)

    excluded_classes = AttributeProperty([
        CharacterClass.MAGE, CharacterClass.CLERIC,
    ])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("rapier", category="weapon_type")
