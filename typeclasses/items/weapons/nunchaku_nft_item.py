"""
NunchakuNFTItem — nunchaku-type weapons.

NunchakuMixin defines all mastery tables and overrides — shared by
both NunchakuNFTItem (player weapons) and MobNunchaku (mob weapons).

Linked sticks swung at high speed. Two-handed stun specialist.
Ninja only.

Mastery progression:
    UNSKILLED: -2 hit, 1 attack, no stun
    BASIC:      0 hit, 1 attack, no stun
    SKILLED:   +2 hit, 2 attacks, 1 stun check/round
    EXPERT:    +4 hit, 2 attacks, 1 stun check/round
    MASTER:    +6 hit, 3 attacks, 1 stun check/round (PRONE on win by >=5)
    GM:        +8 hit, 3 attacks, 2 stun checks/round (PRONE on win by >=5, 2 rounds)

Two-handed, no dual-wield. GARGANTUAN only immune to stun.

Stun/Knockdown (SKILLED+):
    Contested DEX roll: attacker d20 + DEX bonus + mastery bonus VS
    defender d20 + CON bonus. Size-gated: GARGANTUAN immune.

    SKILLED/EXPERT: attacker wins → target STUNNED 1 round
    MASTER: win by <5 → STUNNED 1 round, win by >=5 → PRONE 1 round
    GM: win by <5 → STUNNED 2 rounds, win by >=5 → PRONE 2 rounds
"""

from evennia.typeclasses.attributes import AttributeProperty
from enums.unused_for_reference.damage_type import DamageType

from enums.actor_size import ActorSize
from enums.character_class import CharacterClass
from enums.mastery_level import MasteryLevel
from combat.combat_utils import get_actor_size
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

_NUNCHAKU_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 2,
    MasteryLevel.GRANDMASTER: 2,
}

_NUNCHAKU_STUN_CHECKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

# Sizes immune to nunchaku stun/knockdown
_STUN_IMMUNE_SIZES = {ActorSize.GARGANTUAN}


class NunchakuMixin:
    """Nunchaku weapon identity — mastery tables and overrides.

    Shared by NunchakuNFTItem and MobNunchaku. Single source of truth
    for nunchaku combat mechanics.
    """

    weapon_type_key = "nanchaku"
    base_damage = AttributeProperty("d4")
    speed = AttributeProperty(2)
    weight = AttributeProperty(1.0)
    two_handed = AttributeProperty(True)
    can_dual_wield = AttributeProperty(False)

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NUNCHAKU_EXTRA_ATTACKS.get(mastery, 0)

    def get_stun_checks_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NUNCHAKU_STUN_CHECKS.get(mastery, 0)

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_hit(self, wielder, target, damage, damage_type):
        """Stun check on hit (SKILLED+)."""
        self._try_stun(wielder, target)
        return damage

    def _try_stun(self, wielder, target):
        """Contested DEX vs CON stun attempt."""
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value < MasteryLevel.SKILLED.value:
            return

        # Size gate
        target_size = get_actor_size(target)
        if target_size in _STUN_IMMUNE_SIZES:
            return

        # Anti-stacking
        if target.has_effect("stunned") or target.has_effect("prone"):
            return

        # Check stun checks remaining this round
        handler = wielder.scripts.get("combat_handler")
        if not handler:
            return
        handler = handler[0]
        if handler.stun_checks_remaining <= 0:
            return

        # Consume one check
        handler.stun_checks_remaining -= 1

        # Contested roll: d20 + DEX bonus + mastery bonus vs d20 + CON bonus
        attacker_roll = (
            dice.roll("1d20")
            + wielder.get_attribute_bonus(wielder.dexterity)
            + mastery.bonus
        )
        defender_roll = (
            dice.roll("1d20")
            + target.get_attribute_bonus(target.constitution)
        )

        if attacker_roll <= defender_roll:
            return

        gap = attacker_roll - defender_roll

        # Determine effect based on mastery
        if mastery.value >= MasteryLevel.MASTER.value:
            rounds = 2 if mastery == MasteryLevel.GRANDMASTER else 1
            if gap >= 5:
                self._apply_prone(wielder, target, rounds)
            else:
                self._apply_stun(wielder, target, rounds)
        else:
            self._apply_stun(wielder, target, rounds=1)

    def _apply_stun(self, wielder, target, rounds):
        """Apply STUNNED — target loses actions for N rounds."""
        applied = target.apply_stunned(rounds, source=wielder)
        if not applied:
            return

        wielder.msg(
            f"|g*STUN* Your nunchaku strikes stun {target.key} "
            f"for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )
        target.msg(
            f"|r*STUN* {wielder.key}'s nunchaku strikes stun you "
            f"for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|y*STUN* {wielder.key}'s nunchaku strikes stun {target.key} "
                f"for {rounds} round{'s' if rounds > 1 else ''}!|n",
                exclude=[wielder, target],
            )

    def _apply_prone(self, wielder, target, rounds):
        """Apply PRONE — target loses actions + all enemies get advantage."""
        applied = target.apply_prone(rounds, source=wielder)
        if not applied:
            return

        wielder.msg(
            f"|g*KNOCKDOWN* Your nunchaku sends {target.key} sprawling "
            f"for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )
        target.msg(
            f"|r*KNOCKDOWN* {wielder.key}'s nunchaku sends you sprawling "
            f"for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )
        if wielder.location:
            wielder.location.msg_contents(
                f"|y*KNOCKDOWN* {wielder.key}'s nunchaku sends {target.key} sprawling "
                f"for {rounds} round{'s' if rounds > 1 else ''}!|n",
                exclude=[wielder, target],
            )


class NunchakuNFTItem(NunchakuMixin, WeaponNFTItem):
    """
    Nunchaku weapons — two-handed melee, stun specialist.

    Contested DEX vs CON stun on hit. PRONE at MASTER+ on big wins.
    GARGANTUAN only immune to stun. Ninja only.
    """

    required_classes = AttributeProperty([CharacterClass.NINJA])

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("nanchaku", category="weapon_type")
