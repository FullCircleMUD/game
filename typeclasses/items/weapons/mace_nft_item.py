"""
MaceNFTItem — mace-type weapons with anti-armor crush mastery.

Maces are one-handed bludgeoning weapons that excel against armoured
targets. Their crush mechanic deals bonus damage that scales with the
target's equipment AC — the heavier the armour, the more bonus damage.
At high mastery, maces also gain extra attacks.

Mastery progression:
    UNSKILLED: -2 hit, no crush, 0 extra attacks
    BASIC:      0 hit, no crush, 0 extra attacks
    SKILLED:   +2 hit, crush cap 2, 0 extra attacks
    EXPERT:    +4 hit, crush cap 3, 0 extra attacks
    MASTER:    +6 hit, crush cap 4, 1 extra attack
    GM:        +8 hit, crush cap 5, 1 extra attack

Anti-Armor Crush mechanic:
    On hit → check target's armor_class (equipment AC, not DEX).
    bonus = min(mastery_cap, max(0, target.armor_class - 12))
    AC 12 or below: no bonus (unarmored / light armour)
    AC 14: +2 bonus (capped by mastery)
    AC 18: +6 bonus (capped by mastery)
    Rewards targeting plate-wearers; useless vs unarmoured rogues.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem

# Anti-armor crush bonus cap by mastery
_MACE_CRUSH_CAP = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 3,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 5,
}

# AC threshold — bonus only applies vs targets with armor_class above this
_CRUSH_AC_THRESHOLD = 12

# Extra attacks by mastery
_MACE_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}


class MaceNFTItem(WeaponNFTItem):
    """
    Mace weapons — melee, bludgeoning, anti-armor crush mastery.
    """

    weapon_type_key = "mace"
    excluded_classes = AttributeProperty([CharacterClass.MAGE])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("mace", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _MACE_EXTRA_ATTACKS.get(mastery, 0)

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """On-hit crush check — bonus damage vs armoured targets."""
        bonus = self._calc_crush_bonus(wielder, target)
        if bonus > 0:
            damage += bonus
            wielder.msg(
                f"|r*CRUSH* Your mace punches through {target.key}'s "
                f"armour for +{bonus} bonus damage!|n"
            )
            target.msg(
                f"|r*CRUSH* {wielder.key}'s mace punches through your "
                f"armour for +{bonus} bonus damage!|n"
            )
            if wielder.location:
                wielder.location.msg_contents(
                    f"|r*CRUSH* {wielder.key}'s mace punches through "
                    f"{target.key}'s armour!|n",
                    exclude=[wielder, target],
                )
        return damage

    def _calc_crush_bonus(self, wielder, target):
        """
        Calculate anti-armor crush bonus damage.

        Uses target.armor_class (equipment AC only, not DEX) to determine
        how heavily armoured they are. Bonus scales with excess AC above
        threshold, capped by wielder's mastery tier.
        """
        mastery = self.get_wielder_mastery(wielder)
        cap = _MACE_CRUSH_CAP.get(mastery, 0)
        if cap <= 0:
            return 0

        target_ac = getattr(target, "armor_class", 10)
        excess = target_ac - _CRUSH_AC_THRESHOLD
        if excess <= 0:
            return 0

        return min(cap, excess)
