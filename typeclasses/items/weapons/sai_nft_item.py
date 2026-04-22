"""
SaiNFTItem — sai-type weapons.

SaiMixin defines all mastery tables and overrides — shared by
both SaiNFTItem (player weapons) and MobSai (mob weapons).

A pronged defensive weapon. Pure parry specialist — the highest parry
count of any one-handed weapon. On a successful parry, the sai wielder
can attempt to disarm the attacker via a contested DEX vs STR roll.

Mastery progression:
    UNSKILLED: -2 hit, 1 attack, 0 parries, 0 disarm checks
    BASIC:      0 hit, 1 attack, 1 parry,   0 disarm checks
    SKILLED:   +2 hit, 1 attack, 2 parries, 1 disarm check
    EXPERT:    +4 hit, 1 attack, 3 parries, 1 disarm check
    MASTER:    +6 hit, 1 attack, 4 parries, 1 disarm check
    GM:        +8 hit, 1 attack, 5 parries, 2 disarm checks

Disarm-on-parry (SKILLED+):
    Contested DEX roll: wielder d20 + DEX bonus + mastery bonus VS
    attacker d20 + STR bonus. Attacker more than 1 size larger than the
    sai wielder is immune. On success, attacker's weapon is unequipped
    to their inventory.

No extra attacks, no off-hand, no parry advantage, no riposte.
Dual-wieldable. Ninja only.
"""

import logging

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.size import size_value
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from combat.combat_utils import get_actor_size, force_drop_weapon, get_weapon
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

logger = logging.getLogger("evennia")

_SAI_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 1,
    MasteryLevel.SKILLED: 2,
    MasteryLevel.EXPERT: 3,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 5,
}

_SAI_DISARM_CHECKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}


class SaiMixin:
    """Sai weapon identity — mastery tables and overrides.

    Shared by SaiNFTItem and MobSai. Single source of truth
    for sai combat mechanics.
    """

    weapon_type_key = "sai"
    base_damage = AttributeProperty("d4")
    damage_type = AttributeProperty(DamageType.PIERCING)
    speed = AttributeProperty(3)
    weight = AttributeProperty(0.8)
    can_dual_wield = AttributeProperty(True)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_PARRIES.get(mastery, 0)

    def get_extra_attacks(self, wielder):
        return 0

    def get_disarm_checks_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_DISARM_CHECKS.get(mastery, 0)

    # ================================================================== #
    #  Disarm-on-Parry
    # ================================================================== #

    def _try_disarm(self, wielder, attacker):
        """Attempt to disarm the attacker after a successful parry.

        Contested DEX + mastery (wielder) vs STR (attacker).
        Called from the parry success block in execute_attack().

        Args:
            wielder: the sai wielder (defender who just parried)
            attacker: the combatant whose attack was parried
        """
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value < MasteryLevel.SKILLED.value:
            return

        # Size gate — attacker more than 1 size larger than wielder is immune
        wielder_size = get_actor_size(wielder)
        attacker_size = get_actor_size(attacker)
        if size_value(attacker_size) > size_value(wielder_size) + 1:
            return

        # Check attacker has a real weapon (don't waste a check on unarmed)
        attacker_weapon = get_weapon(attacker)
        if not attacker_weapon or not hasattr(attacker_weapon, "weapon_type_key"):
            return
        from typeclasses.items.weapons.unarmed_weapon import UnarmedWeapon
        if isinstance(attacker_weapon, UnarmedWeapon):
            return

        # Check disarm checks remaining on wielder's handler
        handler = wielder.scripts.get("combat_handler")
        if not handler:
            return
        handler = handler[0]
        if handler.disarm_checks_remaining <= 0:
            return

        # Consume one check
        handler.disarm_checks_remaining -= 1

        # Contested roll: d20 + DEX + mastery vs d20 + STR
        disarmer_roll = (
            dice.roll("1d20")
            + wielder.get_attribute_bonus(wielder.dexterity)
            + mastery.bonus
        )
        defender_roll = (
            dice.roll("1d20")
            + attacker.get_attribute_bonus(attacker.strength)
        )

        if disarmer_roll <= defender_roll:
            return

        # Disarm succeeded
        success, weapon_name = force_drop_weapon(attacker)
        if not success:
            return

        # Three-perspective messages
        wielder.msg(
            f"|g*DISARM* You catch {attacker.key}'s {weapon_name} "
            f"with your sai and wrench it free!|n"
        )
        attacker.msg(
            f"|r*DISARM* {wielder.key}'s sai catches your {weapon_name} "
            f"and wrenches it from your grip!|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|y*DISARM* {wielder.key}'s sai catches "
                f"{attacker.key}'s {weapon_name} and wrenches it free!|n",
                exclude=[wielder, attacker],
            )


class SaiNFTItem(SaiMixin, WeaponNFTItem):
    """
    Sai weapons — one-handed melee, pure parry specialist.

    Highest parry count of any one-handed weapon (up to 5 at GM).
    Disarm-on-parry at SKILLED+ via contested DEX vs STR roll.
    No extra attacks, no off-hand attacks, no parry advantage, no riposte.
    GARGANTUAN immune to disarm. Ninja only.
    """

    required_classes = AttributeProperty([CharacterClass.NINJA])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("sai", category="weapon_type")
