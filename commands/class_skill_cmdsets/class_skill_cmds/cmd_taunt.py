"""
Taunt — provoke an enemy mob into attacking you.

PROTECT skill (warrior, paladin). Contested CHA vs WIS roll.

Two paths:
  Opener (out of combat): Roll first. Success = mob attacks taunter (mob is
    the combat initiator — useful for future crime/guard tracking). Failure =
    5-minute cooldown to prevent spam.
  In combat: Success = mob switches target to taunter. Failure = message only.
    Round-based cooldown scales with mastery.

Only works on CombatMobs — taunting players has no mechanical effect without
a PC aggro system.

Usage:
    taunt <target>    — taunt a specific enemy mob
    taunt             — in combat: taunt current attack target
                        out of combat: "Taunt who?"
"""

import random
import time

from combat.combat_utils import get_sides
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from .cmd_skill_base import CmdSkillBase

TAUNT_COOLDOWNS = {
    MasteryLevel.BASIC: 6,
    MasteryLevel.SKILLED: 5,
    MasteryLevel.EXPERT: 4,
    MasteryLevel.MASTER: 3,
    MasteryLevel.GRANDMASTER: 2,
}

TAUNT_OOC_FAIL_COOLDOWN = 300  # 5 minutes in seconds


class CmdTaunt(CmdSkillBase):
    """
    Provoke an enemy mob into attacking you.

    Usage:
        taunt <target>
        taunt

    Contested charisma check against the mob's wisdom.
    Success forces the mob to attack you.

    Can be used out of combat to bait a mob into starting a fight —
    the mob is considered the initiator. On failure out of combat,
    a 5-minute cooldown prevents repeated attempts.

    Higher mastery reduces the in-combat cooldown.
    """

    key = "taunt"
    skill = skills.PROTECT.value
    help_category = "Combat"

    def func(self):
        caller = self.caller

        # ── Mastery check ──
        if not (getattr(caller.db, "general_skill_mastery_levels", None)
                or getattr(caller.db, "class_skill_mastery_levels", None)
                or getattr(caller.db, "weapon_skill_mastery_levels", None)):
            return self.mob_func()

        mastery_int = caller.get_skill_mastery(self.skill)
        mastery = MasteryLevel(mastery_int)

        if mastery == MasteryLevel.UNSKILLED:
            caller.msg("You need training in protect before you can taunt.")
            return

        # ── Resolve handler (may be None if not in combat) ──
        handler = None
        handlers = caller.scripts.get("combat_handler")
        if handlers:
            handler = handlers[0]

        in_combat = handler is not None

        # ── Parse target ──
        target = None
        if self.args and self.args.strip():
            target = caller.search(self.args.strip())
            if not target:
                return
        elif in_combat:
            action = handler.action_dict
            if action and action.get("key") == "attack":
                target = action.get("target")
            if not target:
                caller.msg("Taunt who?")
                return
        else:
            caller.msg("Taunt who?")
            return

        # ── Validate target ──
        if target == caller:
            caller.msg("You can't taunt yourself.")
            return

        if not hasattr(target, "hp") or target.hp is None:
            caller.msg("You can't taunt that.")
            return

        if target.hp <= 0:
            caller.msg(f"{target.key} is already dead.")
            return

        if target.location != caller.location:
            caller.msg("They're not here.")
            return

        # ── Must be a CombatMob ──
        from typeclasses.actors.mob import CombatMob
        if not isinstance(target, CombatMob):
            caller.msg("Taunting other players has no effect.")
            return

        # ── Room must allow combat ──
        room = caller.location
        if not getattr(room, "allow_combat", False):
            caller.msg("Combat is not allowed here.")
            return

        # ── Cooldown check ──
        if in_combat:
            if handler.taunt_cooldown > 0:
                caller.msg(
                    f"Taunt is on cooldown ({handler.taunt_cooldown} "
                    f"round{'s' if handler.taunt_cooldown > 1 else ''} remaining)."
                )
                return
        else:
            cooldown_until = caller.db.taunt_cooldown_until or 0
            if time.time() < cooldown_until:
                remaining = int(cooldown_until - time.time())
                mins = remaining // 60
                secs = remaining % 60
                caller.msg(
                    f"You're still recovering from your last failed taunt attempt. "
                    f"({mins}m {secs}s remaining)"
                )
                return

        # ── Movement cost ──
        TAUNT_MOVE_COST = 1
        if caller.move < TAUNT_MOVE_COST:
            caller.msg("You are too exhausted to taunt.")
            return
        caller.move = max(0, caller.move - TAUNT_MOVE_COST)

        # ── Must be an enemy (if in combat) ──
        if in_combat:
            _, enemies = get_sides(caller)
            if target not in enemies:
                caller.msg(f"{target.key} is not an enemy.")
                return

        # ── Contested roll: CHA + mastery vs target WIS ──
        attacker_roll = dice.roll("1d20")
        cha_mod = caller.get_attribute_bonus(caller.charisma)
        attacker_total = attacker_roll + cha_mod + mastery.bonus

        defender_roll = dice.roll("1d20")
        wis_mod = target.get_attribute_bonus(target.wisdom)
        defender_total = defender_roll + wis_mod

        if in_combat:
            # ── IN-COMBAT PATH ──
            handler.taunt_cooldown = TAUNT_COOLDOWNS[mastery]

            if attacker_total > defender_total:
                # Success — switch mob's target
                target_handlers = target.scripts.get("combat_handler")
                if target_handlers:
                    dt = random.randint(
                        target.attack_delay_min, target.attack_delay_max
                    )
                    target_handlers[0].queue_action({
                        "key": "attack",
                        "target": caller,
                        "dt": dt,
                        "repeat": True,
                    })

                caller.msg(
                    f"|g*TAUNT* You goad {target.key} into attacking you!|n "
                    f"(Taunt: {attacker_roll} + {cha_mod + mastery.bonus} = {attacker_total} "
                    f"vs {defender_total})"
                )
                target.msg(
                    f"|r{caller.key} taunts you, drawing your attention!|n"
                )
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} taunts {target.key}, drawing its attention!|n",
                        exclude=[caller, target],
                    )
            else:
                # Failure
                caller.msg(
                    f"|rYou try to taunt {target.key} but it ignores you.|n "
                    f"(Taunt: {attacker_roll} + {cha_mod + mastery.bonus} = {attacker_total} "
                    f"vs {defender_total})"
                )
        else:
            # ── OPENER PATH ──
            if attacker_total > defender_total:
                # Success — mob takes the bait and attacks
                # initiate_attack triggers enter_combat from the mob's side
                target.initiate_attack(caller)

                # Ensure caller has a handler + attack action
                handlers = caller.scripts.get("combat_handler")
                if handlers:
                    handler = handlers[0]
                    from django.conf import settings as django_settings
                    dt = getattr(django_settings, "COMBAT_TICK_INTERVAL", 4.0)
                    init_delay = getattr(handler.ndb, "initiative_delay", 0) or 0
                    handler.queue_action({
                        "key": "attack",
                        "target": target,
                        "dt": dt,
                        "repeat": True,
                        "initial_delay": init_delay,
                    })
                    handler.taunt_cooldown = TAUNT_COOLDOWNS[mastery]

                caller.msg(
                    f"|g*TAUNT* You provoke {target.key} into attacking!|n "
                    f"(Taunt: {attacker_roll} + {cha_mod + mastery.bonus} = {attacker_total} "
                    f"vs {defender_total})"
                )
                caller.msg(f"|r{target.key} attacks you!|n")
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} provokes {target.key} into attacking!|n",
                        exclude=[caller, target],
                    )
            else:
                # Failure — mob ignores, 5-minute cooldown
                caller.db.taunt_cooldown_until = time.time() + TAUNT_OOC_FAIL_COOLDOWN
                caller.msg(
                    f"|r{target.key} ignores your taunts.|n "
                    f"(Taunt: {attacker_roll} + {cha_mod + mastery.bonus} = {attacker_total} "
                    f"vs {defender_total})"
                )

    # ── Mob fallback ──
    def mob_func(self):
        pass

    # Mastery stubs — not used (func overridden)
    def unskilled_func(self):
        pass

    def basic_func(self):
        pass

    def skilled_func(self):
        pass

    def expert_func(self):
        pass

    def master_func(self):
        pass

    def grandmaster_func(self):
        pass
