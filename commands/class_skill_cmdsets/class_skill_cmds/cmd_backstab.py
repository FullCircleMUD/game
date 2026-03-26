"""
Stab — 5e-style Sneak Attack for thieves.

When the thief has advantage against a target (HIDDEN, target ENTANGLED,
flanking, etc.), stab adds bonus damage dice to their next attack. Can be
used as a combat opener from stealth or mid-combat whenever advantage exists.

Bonus damage scales with STAB mastery:
  BASIC: +2d6    SKILLED: +4d6    EXPERT: +6d6
  MASTER: +8d6   GRANDMASTER: +10d6

Critical hits double the bonus dice. Once per round. Consumes advantage.

Usage:
    stab <target>
    stab                — defaults to current combat target
    backstab <target>   — alias
    bs <target>         — alias
"""

from combat.combat_utils import enter_combat, get_weapon
from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase

STAB_DICE = {
    MasteryLevel.BASIC: "2d6",
    MasteryLevel.SKILLED: "4d6",
    MasteryLevel.EXPERT: "6d6",
    MasteryLevel.MASTER: "8d6",
    MasteryLevel.GRANDMASTER: "10d6",
}


class CmdBackstab(CmdSkillBase):
    """
    Deal bonus damage when you have advantage.

    Usage:
        stab <target>
        stab

    5e-style sneak attack. When you have advantage against a target,
    stab adds bonus damage dice to your next attack. Can be used as
    an opener from stealth or mid-combat whenever advantage exists.

    Once per round. Critical hits double the bonus dice.
    """

    key = "stab"
    aliases = ["backstab", "bs"]
    skill = skills.STAB.value
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
            caller.msg("You need training in stab before you can use it.")
            return

        # ── Parse target ──
        handler = None
        handlers = caller.scripts.get("combat_handler")
        if handlers:
            handler = handlers[0]

        target = None
        if self.args and self.args.strip():
            results = caller.search(self.args.strip(), location=caller.location, quiet=True)
            if not results:
                caller.msg(f"You don't see '{self.args.strip()}' here.")
                return
            target = results[0] if isinstance(results, list) else results
        elif handler:
            # Default to current attack target
            action = handler.action_dict
            if action and action.get("key") == "attack":
                target = action.get("target")
            if not target:
                caller.msg("Stab who?")
                return
        else:
            caller.msg("Stab who?")
            return

        # ── Validate target ──
        if target == caller:
            caller.msg("You can't stab yourself.")
            return

        if not hasattr(target, "hp") or target.hp is None:
            caller.msg("You can't stab that.")
            return

        if target.hp <= 0:
            caller.msg(f"{target.key} is already dead.")
            return

        if target.location != caller.location:
            caller.msg("They're not here.")
            return

        # ── Room must allow combat ──
        room = caller.location
        if not getattr(room, "allow_combat", False):
            caller.msg("Combat is not allowed here.")
            return

        # ── Must be wielding a finesse melee weapon ──
        weapon = get_weapon(caller)
        if not weapon or not getattr(weapon, "is_finesse", False):
            caller.msg("You need a finesse weapon to stab.")
            return
        if getattr(weapon, "weapon_type", "melee") != "melee":
            caller.msg("You can't stab with a ranged weapon.")
            return

        # ── Determine advantage source ──
        in_combat = handler is not None
        is_hidden = (
            hasattr(caller, "has_condition")
            and caller.has_condition(Condition.HIDDEN)
        )

        if in_combat:
            # Mid-combat: must have advantage
            if not handler.has_advantage(target) and not is_hidden:
                caller.msg("You need advantage to use stab!")
                return

            # Once-per-round check
            if handler.stab_used:
                caller.msg("You already used stab this round.")
                return

            # If hidden mid-combat, break hidden and grant advantage
            if is_hidden:
                caller.remove_condition(Condition.HIDDEN)
                handler.set_advantage(target, rounds=1)
                caller.msg("|yYou slip out of the shadows...|n")

        else:
            # Opener: must be hidden
            if not is_hidden:
                caller.msg("You need advantage to use stab!")
                return

        # ── Get bonus dice ──
        bonus_dice = STAB_DICE.get(mastery)
        if not bonus_dice:
            caller.msg("You need training in stab before you can use it.")
            return

        # ── Execute ──
        if not in_combat:
            # OPENER PATH — from stealth
            caller.remove_condition(Condition.HIDDEN)

            if not enter_combat(caller, target):
                return

            handlers = caller.scripts.get("combat_handler")
            if not handlers:
                caller.msg("Something went wrong entering combat.")
                return
            handler = handlers[0]

            handler.set_advantage(target, rounds=1)

            # Queue repeating attack action
            weapon = caller.get_slot("WIELD") if hasattr(caller, "get_slot") else None
            speed = getattr(weapon, "speed", 1.0) if weapon else 1.0
            dt = max(2, int(4 / speed))

            handler.queue_action({
                "key": "attack",
                "target": target,
                "dt": dt,
                "repeat": True,
            })

            handler.bonus_attack_dice = bonus_dice
            handler.stab_used = True

            caller.msg(
                f"|yYou strike from the shadows, aiming for a vital spot! "
                f"(+{bonus_dice})|n"
            )
            caller.msg(f"|rYou attack {target.key}!|n")
        else:
            # MID-COMBAT PATH
            handler.bonus_attack_dice = bonus_dice
            handler.stab_used = True

            caller.msg(
                f"|yYou aim for a vital spot! (+{bonus_dice})|n"
            )
