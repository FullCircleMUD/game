"""
Bash — knock an enemy prone with a powerful strike.

BASH skill (warrior). High risk / high reward combat maneuver.
Contested roll: d20 + STR mod + mastery bonus vs target d20 + STR mod.

Success: target is knocked PRONE for 1 round — loses their turn and all
enemies get advantage against them (handled by named effect callback).

Failure: basher must make a DEX save (DC 10 + mastery bonus) or fall
prone themselves from overextending.

Cooldown scales with mastery (fewer rounds at higher mastery).
The cooldown only prevents re-using bash — normal attacks continue.

Usage:
    bash <target>     — bash a specific enemy (starts combat if needed)
    bash              — in combat: bash current attack target
                        out of combat: stumble awkwardly
"""

from combat.combat_utils import enter_combat, get_sides
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from utils.dice_roller import dice
from utils.targeting.helpers import (
    resolve_attack_target_in_combat,
    resolve_attack_target_out_of_combat,
)
from .cmd_skill_base import CmdSkillBase

BASH_COOLDOWNS = {
    MasteryLevel.BASIC: 7,
    MasteryLevel.SKILLED: 6,
    MasteryLevel.EXPERT: 5,
    MasteryLevel.MASTER: 4,
    MasteryLevel.GRANDMASTER: 3,
}


class CmdBash(CmdSkillBase):
    """
    Knock an enemy prone with a powerful strike.

    Usage:
        bash <target>
        bash

    Contested strength check. Success knocks the target prone —
    they lose their next turn and all your allies get advantage.
    Failure risks knocking yourself prone from overextending.

    Can start combat if used on a target while out of combat.
    With no argument, defaults to your current attack target.

    Higher mastery reduces the cooldown between uses.
    """

    key = "bash"
    aliases = []
    skill = skills.BASH.value
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
            caller.msg("You need training in bash before you can use it.")
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
            search_term = self.args.strip()
            if in_combat:
                target = resolve_attack_target_in_combat(caller, search_term)
            else:
                target = resolve_attack_target_out_of_combat(caller, search_term)
            if target is None:
                caller.msg(f"You don't see '{search_term}' here.")
                return
        elif in_combat:
            # Default to current attack target
            action = handler.action_dict
            if action and action.get("key") == "attack":
                target = action.get("target")
            if not target:
                caller.msg("Bash who?")
                return
        else:
            # No args, not in combat — funny message
            caller.msg(
                "You charge forward with a mighty bash... and trip over "
                "your own feet. Maybe find an enemy first."
            )
            return

        # ── Validate target ──
        if target == caller:
            caller.msg("You can't bash yourself.")
            return

        if target.location != caller.location:
            caller.msg("They're not here.")
            return

        # ── Room must allow combat ──
        room = caller.location
        if not getattr(room, "allow_combat", False):
            caller.msg("Combat is not allowed here.")
            return

        # ── Enter combat if needed ──
        if not in_combat:
            if not enter_combat(caller, target):
                return

            handlers = caller.scripts.get("combat_handler")
            if not handlers:
                caller.msg("Something went wrong entering combat.")
                return
            handler = handlers[0]

            # Queue repeating attack with initiative delay
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

            caller.msg(f"|rYou charge at {target.key}!|n")

        # ── Target must be in combat ──
        target_handlers = target.scripts.get("combat_handler")
        if not target_handlers:
            caller.msg(f"{target.key} is not in combat.")
            return

        # ── Must be an enemy ──
        _, enemies = get_sides(caller)
        if target not in enemies:
            caller.msg(f"{target.key} is not an enemy.")
            return

        # ── Cooldown check ──
        if handler.skill_cooldown > 0:
            caller.msg(
                f"Combat skill cooldown ({handler.skill_cooldown} "
                f"round{'s' if handler.skill_cooldown > 1 else ''} remaining)."
            )
            return

        # ── Movement cost ──
        BASH_MOVE_COST = 2
        if caller.move < BASH_MOVE_COST:
            caller.msg("You are too exhausted to bash.")
            return
        caller.move = max(0, caller.move - BASH_MOVE_COST)

        # ── Contested roll: STR + mastery vs target STR ──
        attacker_roll = dice.roll("1d20")
        attacker_str = caller.get_attribute_bonus(caller.strength)
        attacker_total = attacker_roll + attacker_str + mastery.bonus

        defender_roll = dice.roll("1d20")
        defender_str = target.get_attribute_bonus(target.strength)
        defender_total = defender_roll + defender_str

        # Set cooldown regardless of outcome
        handler.skill_cooldown = BASH_COOLDOWNS[mastery]

        if attacker_total > defender_total:
            # ── Success: knock target prone ──
            applied = target.apply_named_effect(
                key="prone", source=caller,
                duration=1, duration_type="combat_rounds",
            )

            if applied:
                caller.msg(
                    f"|g*BASH* You slam into {target.key}, knocking them to the ground!|n "
                    f"(Bash: {attacker_roll} + {attacker_str + mastery.bonus} = {attacker_total} "
                    f"vs {defender_total})"
                )
                target.msg(
                    f"|r*BASH* {caller.key} slams into you, knocking you to the ground!|n "
                    f"({defender_roll} + {defender_str} = {defender_total} "
                    f"vs {attacker_total})"
                )
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} bashes {target.key} to the ground!|n",
                        exclude=[caller, target],
                    )
            else:
                # Target already prone (anti-stacking)
                caller.msg(
                    f"|yYou bash {target.key} but they're already on the ground.|n "
                    f"(Bash: {attacker_roll} + {attacker_str + mastery.bonus} = {attacker_total} "
                    f"vs {defender_total})"
                )
        else:
            # ── Failure: DEX save or fall prone ──
            caller.msg(
                f"|rYou try to bash {target.key} but miss!|n "
                f"(Bash: {attacker_roll} + {attacker_str + mastery.bonus} = {attacker_total} "
                f"vs {defender_total})"
            )

            # DEX save: DC 10, add DEX mod + mastery bonus
            dex_roll = dice.roll("1d20")
            dex_mod = caller.get_attribute_bonus(caller.dexterity)
            dex_total = dex_roll + dex_mod + mastery.bonus
            dex_dc = 10

            if dex_total < dex_dc:
                # Failed DEX save — basher falls prone
                caller.apply_named_effect(
                    key="prone", source=target,
                    duration=1, duration_type="combat_rounds",
                )
                caller.msg(
                    f"|r*BASH FAIL* You overextend and fall prone!|n "
                    f"(DEX save: {dex_roll} + {dex_mod + mastery.bonus} = {dex_total} "
                    f"vs DC {dex_dc})"
                )
                target.msg(
                    f"|g{caller.key} overextends trying to bash you and falls prone!|n"
                )
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} overextends a bash and falls to the ground!|n",
                        exclude=[caller, target],
                    )

    # ── Mob fallback ──
    def mob_func(self):
        """Mobs don't use bash (they have their own AI)."""
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
