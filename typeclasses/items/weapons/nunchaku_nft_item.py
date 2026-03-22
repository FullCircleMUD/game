"""
NunchakuNFTItem — nunchaku-type weapons.

Linked sticks swung at high speed. Stun specialist with dual-wield.
Usable by warriors, ninjas, and barbarians.

Mastery progression:
    UNSKILLED: -2 hit, 0 extra attacks, 0 off-hand, no stun
    BASIC:      0 hit, 0 extra attacks, 0 off-hand, no stun
    SKILLED:   +2 hit, 0 extra attacks, 1 off-hand (-4), 1 stun check/round
    EXPERT:    +4 hit, 0 extra attacks, 1 off-hand (-2), 1 stun check/round
    MASTER:    +6 hit, +1 extra attack, 1 off-hand (0), 1 stun check/round (PRONE on win by >=5)
    GM:        +8 hit, +1 extra attack, 2 off-hand (0), 2 stun checks/round (PRONE on win by >=5, 2 rounds)

Stun/Knockdown (SKILLED+):
    Contested DEX roll: attacker d20 + DEX bonus + mastery bonus VS
    defender d20 + CON bonus. Size-gated: HUGE+ enemies are immune.

    SKILLED/EXPERT: attacker wins → target STUNNED 1 round
    MASTER: win by <5 → STUNNED 1 round, win by >=5 → PRONE 1 round
    GM: win by <5 → STUNNED 2 rounds, win by >=5 → PRONE 2 rounds
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.actor_size import ActorSize
from enums.mastery_level import MasteryLevel
from combat.combat_utils import get_actor_size
from typeclasses.items.weapons.weapon_nft_item import WeaponNFTItem
from utils.dice_roller import dice

_NUNCHAKU_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 0,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

_NUNCHAKU_OFFHAND_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 1,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 2,
}

_NUNCHAKU_OFFHAND_PENALTY = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: -4,
    MasteryLevel.EXPERT: -2,
    MasteryLevel.MASTER: 0,
    MasteryLevel.GRANDMASTER: 0,
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
_STUN_IMMUNE_SIZES = {ActorSize.HUGE, ActorSize.GARGANTUAN}


class NunchakuNFTItem(WeaponNFTItem):
    """
    Nunchaku weapons — one-handed melee, stun specialist + dual-wield.

    Contested DEX vs CON stun on hit. PRONE at MASTER+ on big wins.
    """

    weapon_type_key = "nanchaku"
    can_dual_wield = AttributeProperty(True)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("nanchaku", category="weapon_type")

    # ================================================================== #
    #  Mastery Overrides
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NUNCHAKU_EXTRA_ATTACKS.get(mastery, 0)

    def get_offhand_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NUNCHAKU_OFFHAND_ATTACKS.get(mastery, 0)

    def get_offhand_hit_modifier(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _NUNCHAKU_OFFHAND_PENALTY.get(mastery, 0)

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
