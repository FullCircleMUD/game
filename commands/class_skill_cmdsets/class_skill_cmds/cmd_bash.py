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

from combat.combat_utils import (
    enter_combat,
    fight_refusal_message,
    get_actor_size,
    get_sides,
)
from enums.mastery_level import MasteryLevel
from enums.size import size_value
from enums.skills_enum import skills
from utils.dice_roller import dice
from utils.targeting.helpers import resolve_target
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

        # ── Can this actor pick a fight right now? ──
        ok, reason = caller._can_start_fight_now()
        if not ok:
            caller.msg(fight_refusal_message(reason))
            return

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
            # Through the front door: resolve_target runs the same
            # in-combat/out-of-combat dispatch and sends its own refusal,
            # and it is the only place a predicate can be attached. You
            # cannot pick a fight with someone you cannot see.
            # Filtering lives in the resolvers, not here: p_living, then
            # p_can_see out of combat (picking a fight needs eyes) or
            # p_can_perceive in combat (you swing at what you can sense).
            target, _ = resolve_target(
                caller, search_term, "actor_hostile",
            )
            if target is None:
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

        # ── Size gate: can only bash targets up to 1 size larger ──
        caller_size = get_actor_size(caller)
        target_size = get_actor_size(target)
        if size_value(target_size) > size_value(caller_size) + 1:
            caller.msg(
                f"|y{target.key} is too large for you to knock down!|n"
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
        BASH_MOVE_COST = 2
        if caller.move < BASH_MOVE_COST:
            caller.msg("You are too exhausted to bash.")
            return
        caller.move = max(0, caller.move - BASH_MOVE_COST)

        # Concealment is not broken here. A basher is in combat by this
        # point, so an auto-attack is running each round, and every one of
        # them goes through `execute_attack`, which calls
        # `break_conditions_from_hostile_action`. Anyone bashing is
        # therefore already revealed, or is revealed within the round.

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
            from utils.skill_xp import award_skill_xp
            award_skill_xp(caller, getattr(target, "level", 1), target=target)
            applied = target.apply_named_effect(
                key="prone", source=caller,
                duration=1, duration_type="combat_rounds",
            )

            if applied:
                caller.msg(
                    f"|g*BASH* You slam into {target.key}, knocking them to the ground!|n"
                )
                target.msg(
                    f"|r*BASH* {caller.key} slams into you, knocking you to the ground!|n"
                )
                if caller.location:
                    caller.location.msg_contents(
                        "|y{basher} bashes {victim} to the ground!|n",
                        exclude=[caller, target],
                        mapping={"basher": caller, "victim": target},
                    )
            else:
                # Target already prone (anti-stacking)
                caller.msg(
                    f"|yYou bash {target.key} but they're already on the ground.|n"
                )
        else:
            # ── Failure: DEX save or fall prone ──
            caller.msg(
                f"|rYou try to bash {target.key} but miss!|n"
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
                    f"|r*BASH FAIL* You overextend and fall prone!|n"
                )
                target.msg(
                    f"|g{caller.key} overextends trying to bash you and falls prone!|n"
                )
                if caller.location:
                    caller.location.msg_contents(
                        "|y{basher} overextends a bash and falls to the ground!|n",
                        exclude=[caller, target],
                        mapping={"basher": caller},
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
