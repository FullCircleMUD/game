"""
StaffNFTItem — staff-type weapons with parry specialist mastery.

StaffMixin defines all mastery tables and overrides — shared by
both StaffNFTItem (player weapons) and MobStaff (mob weapons).

Staves are two-handed bludgeoning weapons that offer the best defensive
scaling in the game. Highest parry count, earliest parry advantage, and
riposte at high mastery. THE weapon for casters who want to survive melee.

UNIVERSAL PARRY: Staff parries work against ALL physical attack types
(armed melee, unarmed, animal, missile). Other weapons can only parry
armed melee attacks. The combat handler will check `universal_parry`
on the defender's weapon to determine valid parry targets.

Mastery progression:
    UNSKILLED: -2 hit, no parries
    BASIC:      0 hit, no parries
    SKILLED:   +2 hit, 2 parries/round
    EXPERT:    +3 hit, 2 parries/round, advantage on parry rolls
    MASTER:    +4 hit, 3 parries/round, advantage on parry rolls, riposte
    GM:        +5 hit, 4 parries/round, advantage on parry rolls, riposte

Comparison:
    vs Longsword (0/0/1/2/2/3 parries, advantage GM only, NO riposte):
        Staff gets more parries at every tier and earlier advantage.
    vs Rapier (0/0/1/1/2/3 parries, riposte EXPERT+):
        Staff gets more parries and earlier advantage, but rapier gets
        riposte earlier and is finesse.
    Trade-off: Staff is two-handed (no shield), no extra attacks, no finesse.
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Custom hit bonuses — lower at EXPERT+ to offset defensive scaling
_STAFF_HIT_BONUSES = {
    MasteryLevel.UNSKILLED: -2,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 3,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 5,
}

_STAFF_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 2,
    MasteryLevel.MASTER: 3,
    MasteryLevel.GRANDMASTER: 4,
}


class StaffMixin:
    """Staff weapon identity — mastery tables and overrides.

    Shared by StaffNFTItem and MobStaff. Single source of truth
    for staff combat mechanics.
    """

    weapon_type_key = "staff"
    base_damage = AttributeProperty("d6")
    weight = AttributeProperty(2.5)
    two_handed = AttributeProperty(True)
    universal_parry = True

    def get_mastery_hit_bonus(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _STAFF_HIT_BONUSES.get(mastery, 0)

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _STAFF_PARRIES.get(mastery, 0)

    def get_parry_advantage(self, wielder):
        """Parry advantage at EXPERT+ (earlier than any other weapon)."""
        mastery = self.get_wielder_mastery(wielder)
        return mastery.value >= MasteryLevel.EXPERT.value

    def has_riposte(self, wielder):
        """Riposte unlocks at MASTER mastery."""
        mastery = self.get_wielder_mastery(wielder)
        return mastery.value >= MasteryLevel.MASTER.value


class StaffNFTItem(StaffMixin, WeaponNFTItem):
    """
    Staff weapons — two-handed melee, parry specialist mastery path.

    Universal parry: can parry armed melee, unarmed, animal, and missile
    attacks (other weapons can only parry armed melee).
    """

    excluded_classes = AttributeProperty([CharacterClass.THIEF])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("staff", category="weapon_type")
