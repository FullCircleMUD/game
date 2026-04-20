"""
Pummel — stun an enemy with rapid strikes.

PUMMEL skill (warrior, paladin). Low risk / low reward combat maneuver.
Contested roll: d20 + STR mod + mastery bonus vs target d20 + DEX mod.

Success: target is STUNNED for 1 round — loses their turn. Unlike PRONE,
stunned does NOT grant advantage to allies (key differentiator from bash).

Failure: nothing happens — just a miss. No risk to the attacker.

Cooldown scales with mastery (fewer rounds at higher mastery).
The cooldown only prevents re-using pummel — normal attacks continue.

Usage:
    pummel <target>   — pummel a specific enemy (starts combat if needed)
    pummel            — in combat: pummel current attack target
                        out of combat: flail awkwardly
"""

from combat.combat_utils import enter_combat, get_actor_size, get_sides
from enums.mastery_level import MasteryLevel
from enums.size import size_value
from enums.skills_enum import skills
from utils.dice_roller import dice
from utils.targeting.helpers import (
    resolve_attack_target_in_combat,
    resolve_attack_target_out_of_combat,
)
from .cmd_skill_base import CmdSkillBase

PUMMEL_COOLDOWNS = {
    MasteryLevel.BASIC: 8,
    MasteryLevel.SKILLED: 7,
    MasteryLevel.EXPERT: 6,
    MasteryLevel.MASTER: 5,
    MasteryLevel.GRANDMASTER: 4,
}


class CmdPummel(CmdSkillBase):
    """
    Stun an enemy with rapid strikes.

    Usage:
        pummel <target>
        pummel

    Contested check — your strength vs the target's dexterity.
    Success stuns the target for 1 round. Failure has no penalty.

    Can start combat if used on a target while out of combat.
    With no argument, defaults to your current attack target.

    Higher mastery reduces the cooldown between uses.
    """

    key = "pummel"
    aliases = []
    skill = skills.PUMMEL.value
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
            caller.msg("You need training in pummel before you can use it.")
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
                caller.msg("Pummel who?")
                return
        else:
            # No args, not in combat — funny message
            caller.msg(
                "You swing your fists wildly at the air. The air is "
                "unimpressed. Try picking an actual target."
            )
            return

        # ── Validate target ──
        if target == caller:
            caller.msg("You can't pummel yourself.")
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

            caller.msg(f"|rYou rush at {target.key}!|n")

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

        # ── Size gate: can only pummel targets up to 1 size larger ──
        caller_size = get_actor_size(caller)
        target_size = get_actor_size(target)
        if size_value(target_size) > size_value(caller_size) + 1:
            caller.msg(
                f"|y{target.key} is too large for you to stun!|n"
            )
            return

        # ── Cooldown check ──
        if handler.skill_cooldown > 0:
            caller.msg(
                f"Combat skill cooldown ({handler.skill_cooldown} "
                f"round{'s' if handler.skill_cooldown > 1 else ''} remaining)."
            )
            return

        # ── Movement cost ──
        PUMMEL_MOVE_COST = 1
        if caller.move < PUMMEL_MOVE_COST:
            caller.msg("You are too exhausted to pummel.")
            return
        caller.move = max(0, caller.move - PUMMEL_MOVE_COST)

        # ── Contested roll: STR + mastery vs target DEX ──
        attacker_roll = dice.roll("1d20")
        attacker_str = caller.get_attribute_bonus(caller.strength)
        attacker_total = attacker_roll + attacker_str + mastery.bonus

        defender_roll = dice.roll("1d20")
        defender_dex = target.get_attribute_bonus(target.dexterity)
        defender_total = defender_roll + defender_dex

        # Set cooldown regardless of outcome
        handler.skill_cooldown = PUMMEL_COOLDOWNS[mastery]

        if attacker_total > defender_total:
            # ── Success: stun target ──
            applied = target.apply_named_effect(
                key="stunned", source=caller,
                duration=1, duration_type="combat_rounds",
            )

            if applied:
                caller.msg(
                    f"|g*PUMMEL* You pummel {target.key}, stunning them!|n"
                )
                target.msg(
                    f"|r*PUMMEL* {caller.key} pummels you, leaving you stunned!|n"
                )
                if caller.location:
                    caller.location.msg_contents(
                        f"|y{caller.key} pummels {target.key}, stunning them!|n",
                        exclude=[caller, target],
                    )
            else:
                # Target already stunned (anti-stacking)
                caller.msg(
                    f"|yYou pummel {target.key} but they're already stunned.|n"
                )
        else:
            # ── Failure: nothing happens ──
            caller.msg(
                f"|rYour pummel misses {target.key}.|n"
            )

    # ── Mob fallback ──
    def mob_func(self):
        """Mobs don't use pummel (they have their own AI)."""
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
