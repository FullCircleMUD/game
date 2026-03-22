"""
SaiNFTItem — sai-type weapons.

A pronged defensive weapon. Catch blades in the prongs — parry, then
disarm on counter. The ninja's defensive weapon.

Mastery progression:
    UNSKILLED: -2 hit, 0 parries, 0 off-hand, no disarm
    BASIC:      0 hit, 0 parries, 0 off-hand, no disarm
    SKILLED:   +2 hit, 1 parry, 1 off-hand (-4), 1 disarm check/round
    EXPERT:    +4 hit, 2 parries, 1 off-hand (-2), 1 disarm check/round
    MASTER:    +6 hit, 2 parries (adv), 1 off-hand (0), 1 disarm check/round
    GM:        +8 hit, 3 parries (adv, riposte), 2 off-hand (0), 2 disarm checks/round

No extra attacks — defense + debuff focused, DPS from off-hand.

Disarm (SKILLED+):
    On hit, contested DEX + mastery bonus vs target's STR + mastery bonus.
    Win → target's weapon is unequipped to their inventory. They must
    spend a combat round re-wielding. Size-gated: HUGE+ immune.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.actor_size import ActorSize
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from combat.combat_utils import force_drop_weapon, get_actor_size, get_weapon
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

_SAI_PARRIES = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 2,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 3,
}

_SAI_PARRY_ADVANTAGE = {
    MasteryLevel.UNSKILLED: False,
    MasteryLevel.BASIC: False,
    MasteryLevel.SKILLED: False,
    MasteryLevel.EXPERT: False,
    MasteryLevel.MASTER: True,
    MasteryLevel.GRANDMASTER: True,
}

_SAI_OFFHAND_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

_SAI_OFFHAND_PENALTY = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: -4,
    MasteryLevel.EXPERT: -2,
    MasteryLevel.MASTER: 0,
    MasteryLevel.GRANDMASTER: 0,
}

_SAI_DISARM_CHECKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

# Sizes immune to disarm
_DISARM_IMMUNE_SIZES = {ActorSize.HUGE, ActorSize.GARGANTUAN}


class SaiNFTItem(WeaponNFTItem):
    """
    Sai weapons — one-handed melee, parry + disarm specialist.

    Strong parry progression with parry advantage at MASTER+ and
    riposte at GM. Disarm on hit unequips target's weapon.
    Ninja only.
    """

    weapon_type_key = "sai"
    required_classes = AttributeProperty([CharacterClass.NINJA])
    can_dual_wield = AttributeProperty(True)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("sai", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_PARRIES.get(mastery, 0)

    def get_extra_attacks(self, wielder):
        return 0

    def get_parry_advantage(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_PARRY_ADVANTAGE.get(mastery, False)

    def has_riposte(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return mastery == MasteryLevel.GRANDMASTER

    def get_offhand_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_OFFHAND_ATTACKS.get(mastery, 0)

    def get_offhand_hit_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_OFFHAND_PENALTY.get(mastery, 0)

    def get_disarm_checks_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _SAI_DISARM_CHECKS.get(mastery, 0)

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """Disarm check on hit (SKILLED+)."""
        self._try_disarm(wielder, target)
        return damage

    def _try_disarm(self, wielder, target):
        """Contested DEX vs STR disarm attempt. Unequips target's weapon."""
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value < MasteryLevel.SKILLED.value:
            return

        # Size gate
        target_size = get_actor_size(target)
        if target_size in _DISARM_IMMUNE_SIZES:
            return

        # Anti-stacking: target must have a weapon wielded
        target_weapon = get_weapon(target)
        if not target_weapon or not hasattr(target_weapon, "weapon_type_key"):
            return
        # UnarmedWeapon is a singleton, not a DB object — can't unequip it
        from typeclasses.items.weapons.unarmed_weapon import UnarmedWeapon
        if isinstance(target_weapon, UnarmedWeapon):
            return

        # Check disarm checks remaining this round
        handler = wielder.scripts.get("combat_handler")
        if not handler:
            return
        handler = handler[0]
        if handler.disarm_checks_remaining <= 0:
            return

        # Consume one check
        handler.disarm_checks_remaining -= 1

        # Contested roll: d20 + DEX bonus + mastery bonus vs d20 + STR bonus + target mastery bonus
        attacker_roll = (
            dice.roll("1d20")
            + wielder.get_attribute_bonus(wielder.dexterity)
            + mastery.bonus
        )
        target_mastery = target_weapon.get_wielder_mastery(target)
        defender_roll = (
            dice.roll("1d20")
            + target.get_attribute_bonus(target.strength)
            + target_mastery.bonus
        )

        if attacker_roll <= defender_roll:
            return

        # Disarm succeeds — force-drop via shared utility
        dropped, weapon_name = force_drop_weapon(target, weapon=target_weapon)
        if not dropped:
            return

        wielder.msg(
            f"|g*DISARM* You catch {target.key}'s {weapon_name} in your "
            f"sai's prongs and wrench it from their grip!|n"
        )
        target.msg(
            f"|r*DISARM* {wielder.key} catches your {weapon_name} in "
            f"their sai's prongs and wrenches it from your grip!|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|y*DISARM* {wielder.key} wrenches {target.key}'s "
                f"{weapon_name} from their grip!|n",
                exclude=[wielder, target],
            )
