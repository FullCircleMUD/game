"""
UnarmedWeapon — pure Python singleton representing unarmed combat.

NOT an Evennia DB object. Mimics the WeaponNFTItem interface so combat
code can treat unarmed PCs identically to armed PCs. Stateless — all
mutable state lives on the wielder/combat_handler.

Every humanoid actor (FCMCharacter) without a wielded weapon gets this
singleton via get_weapon() in combat_utils.py. Animal mobs (CombatMob)
don't have wearslots and continue using their damage_dice attribute.

Mastery progression:
    UNSKILLED: -2 hit,  1 damage,  0 extra attacks
    BASIC:      0 hit, 1d2 damage, 0 extra attacks
    SKILLED:   +2 hit, 1d3 damage, 0 extra attacks, stun on hit
    EXPERT:    +4 hit, 1d4 damage, 1 extra attack,  stun on hit
    MASTER:    +6 hit, 1d6 damage, 1 extra attack,  stun/knockdown on hit
    GRANDMASTER: +8 hit, 1d8 damage, 1 extra attack, stun/knockdown x2 on hit

Stun/Knockdown (SKILLED+):
    On the first successful hit per round (first 2 at GM), make a
    contested roll: attacker d20 + STR bonus + mastery bonus VS
    defender d20 + CON bonus. Size-gated: HUGE+ enemies are immune.

    SKILLED/EXPERT: attacker wins → target STUNNED 1 round (lose action)
    MASTER: attacker wins by <5 → STUNNED 1 round
            attacker wins by >=5 → PRONE 1 round (lose action + all
            enemies get 1 round advantage)
    GM: same as MASTER but STUNNED = 2 rounds, PRONE = 2 rounds
        (lose 2 actions + enemies get 2 rounds advantage)
"""


from enums.mastery_level import MasteryLevel
from enums.unused_for_reference.damage_type import DamageType
from utils.dice_roller import dice

_UNARMED_DAMAGE = {
    MasteryLevel.UNSKILLED: "1d1",
    MasteryLevel.BASIC: "1d2",
    MasteryLevel.SKILLED: "1d3",
    MasteryLevel.EXPERT: "1d4",
    MasteryLevel.MASTER: "1d6",
    MasteryLevel.GRANDMASTER: "1d8",
}

_UNARMED_EXTRA_ATTACKS = {
    MasteryLevel.UNSKILLED: 0,
    MasteryLevel.BASIC: 0,
    MasteryLevel.SKILLED: 0,
    MasteryLevel.EXPERT: 1,
    MasteryLevel.MASTER: 1,
    MasteryLevel.GRANDMASTER: 1,
}

from enums.actor_size import ActorSize
from combat.combat_utils import get_actor_size

# Sizes immune to unarmed stun/knockdown
_STUN_IMMUNE_SIZES = {ActorSize.HUGE, ActorSize.GARGANTUAN}


class UnarmedWeapon:
    """
    Stateless singleton representing unarmed combat (fists, feet, headbutts).

    Implements the same interface as WeaponNFTItem so combat code can
    call weapon hooks, mastery methods, and damage rolls without checking
    whether the weapon is a real DB object or the unarmed fallback.
    """

    weapon_type_key = "unarmed"
    weapon_type = "melee"
    damage_type = DamageType.BLUDGEONING
    is_finesse = False
    two_handed = False
    speed = 4
    key = "fists"  # for combat messages: "attacks with fists"

    # ================================================================== #
    #  Mastery Helpers
    # ================================================================== #

    def get_wielder_mastery(self, wielder):
        if not hasattr(wielder, "db"):
            return MasteryLevel.UNSKILLED
        mastery_int = (wielder.db.weapon_skill_mastery_levels or {}).get(
            self.weapon_type_key, 0
        )
        try:
            return MasteryLevel(mastery_int)
        except ValueError:
            return MasteryLevel.UNSKILLED

    def get_damage_roll(self, mastery_level=MasteryLevel.UNSKILLED):
        return _UNARMED_DAMAGE.get(mastery_level, "1d1")

    def get_mastery_hit_bonus(self, wielder):
        return self.get_wielder_mastery(wielder).bonus

    def get_mastery_damage_bonus(self, wielder):
        return self.get_wielder_mastery(wielder).bonus

    # ================================================================== #
    #  Mastery-Scaled Combat Methods
    # ================================================================== #

    def get_parries_per_round(self, wielder):
        return 0

    def get_extra_attacks(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        return _UNARMED_EXTRA_ATTACKS.get(mastery, 0)

    def get_parry_advantage(self, wielder):
        return False

    def has_riposte(self, wielder):
        return False

    def get_mastery_crit_threshold_modifier(self, wielder):
        return 0

    def get_offhand_attacks(self, wielder):
        return 0

    def get_offhand_hit_modifier(self, wielder):
        return 0

    def get_stun_checks_per_round(self, wielder):
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value < MasteryLevel.SKILLED.value:
            return 0
        return 2 if mastery == MasteryLevel.GRANDMASTER else 1

    # ================================================================== #
    #  Offensive Combat Hooks
    # ================================================================== #

    def at_pre_attack(self, wielder, target):
        return 0

    def at_hit(self, wielder, target, damage, damage_type):
        """
        On-hit stun/knockdown check (SKILLED+).

        Uses combat_handler.stun_checks_remaining to limit checks per round.
        Size-gated: HUGE+ enemies are immune.
        """
        mastery = self.get_wielder_mastery(wielder)
        if mastery.value < MasteryLevel.SKILLED.value:
            return damage

        # Check size immunity
        target_size = get_actor_size(target)
        if target_size in _STUN_IMMUNE_SIZES:
            return damage

        # Check if we have stun checks remaining this round
        handler = wielder.scripts.get("combat_handler")
        if not handler:
            return damage
        handler = handler[0]
        if handler.stun_checks_remaining <= 0:
            return damage

        # Consume one stun check
        handler.stun_checks_remaining -= 1

        # Contested roll: d20 + STR bonus + mastery bonus vs d20 + CON bonus
        attacker_roll = (
            dice.roll("1d20")
            + wielder.get_attribute_bonus(wielder.strength)
            + mastery.bonus
        )
        defender_roll = (
            dice.roll("1d20")
            + target.get_attribute_bonus(target.constitution)
        )

        if attacker_roll <= defender_roll:
            # Failed — target resists
            return damage

        gap = attacker_roll - defender_roll

        # Determine effect based on mastery
        if mastery.value >= MasteryLevel.MASTER.value:
            # MASTER/GM: gap determines stun vs knockdown
            rounds = 2 if mastery == MasteryLevel.GRANDMASTER else 1
            if gap >= 5:
                self._apply_prone(wielder, target, rounds)
            else:
                self._apply_stun(wielder, target, rounds)
        else:
            # SKILLED/EXPERT: stun only, 1 round
            self._apply_stun(wielder, target, rounds=1)

        return damage

    def _apply_stun(self, wielder, target, rounds):
        """Apply STUNNED — target loses actions for N rounds via named effect."""
        applied = target.apply_stunned(rounds, source=wielder)
        if not applied:
            return

        wielder.msg(
            f"|g*STUN* Your blow stuns {target.key} for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )
        target.msg(
            f"|r*STUN* {wielder.key}'s blow stuns you for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )

    def _apply_prone(self, wielder, target, rounds):
        """Apply PRONE — target loses actions + all enemies get advantage (via callback)."""
        applied = target.apply_prone(rounds, source=wielder)
        if not applied:
            return

        wielder.msg(
            f"|g*KNOCKDOWN* You knock {target.key} to the ground for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )
        target.msg(
            f"|r*KNOCKDOWN* {wielder.key} knocks you to the ground for {rounds} round{'s' if rounds > 1 else ''}!|n"
        )

    def at_crit(self, wielder, target, damage, damage_type):
        return damage

    def at_miss(self, wielder, target):
        pass

    def at_kill(self, wielder, target):
        pass

    def at_post_attack(self, wielder, target, hit, damage_dealt):
        pass

    # ================================================================== #
    #  Defensive Combat Hooks
    # ================================================================== #

    def at_pre_defend(self, wielder, attacker):
        return 0

    def at_wielder_about_to_be_hit(self, wielder, attacker, total_hit, total_ac):
        from combat.reactive_spells import check_reactive_shield
        return check_reactive_shield(wielder)

    def at_wielder_hit(self, wielder, attacker, damage, damage_type):
        return damage

    def at_wielder_receive_crit(self, wielder, attacker, damage, damage_type):
        return damage

    def at_wielder_missed(self, wielder, attacker):
        pass

    # ================================================================== #
    #  Lifecycle Combat Hooks
    # ================================================================== #

    def at_combat_start(self, wielder):
        pass

    def at_combat_end(self, wielder):
        pass

    def at_round_start(self, wielder):
        pass

    def at_round_end(self, wielder):
        pass


# Module-level singleton — import this, not the class
UNARMED = UnarmedWeapon()
