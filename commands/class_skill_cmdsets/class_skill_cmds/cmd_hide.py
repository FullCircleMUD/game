"""
Hide command — attempt to become hidden in the current room.

STEALTH class skill (thief, ninja, bard). Contested check: d20 + effective
stealth bonus vs best passive perception (10 + effective perception bonus)
in the room. Binary outcome — hidden from everyone or nobody.

Moving while HIDDEN automatically triggers a new stealth check against
perceivers in the destination room (handled in character.at_post_move).

Usage:
    hide
"""

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase


def best_passive_perception(room, exclude=None):
    """
    Return the highest passive perception DC among characters in the room.

    Passive perception = 10 + effective_perception_bonus.
    Returns 0 if no valid perceivers (empty room = auto-succeed).
    """
    best = 0
    for obj in room.contents:
        if obj == exclude:
            continue
        if not hasattr(obj, "effective_perception_bonus"):
            continue
        score = 10 + obj.effective_perception_bonus
        if score > best:
            best = score
    return best


class CmdHide(CmdSkillBase):
    """
    Attempt to hide in the current room.

    Usage:
        hide

    Rolls your stealth (d20 + stealth bonus) against the best
    passive perception in the room. If successful, you become
    hidden — invisible to other characters until you take an
    aggressive or noisy action, or are found by a search.

    Moving while hidden automatically tests your stealth against
    perceivers in each new room.
    """

    key = "hide"
    aliases = ["hi"]
    skill = skills.STEALTH.value
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            caller.msg("You have nowhere to hide.")
            return

        # Already hidden
        if caller.has_condition(Condition.HIDDEN):
            caller.msg("You are already hidden.")
            return

        # In combat — can't hide
        if caller.scripts.get("combat_handler"):
            caller.msg("You can't hide while in combat!")
            return

        # Mastery check — UNSKILLED can't hide
        mastery_int = caller.get_skill_mastery(self.skill) if hasattr(caller, 'get_skill_mastery') else 0
        if mastery_int <= 0:
            caller.msg(
                "You have no idea how to hide effectively. "
                "You need training in stealth before you can hide."
            )
            return

        # Best passive perception in room
        dc = best_passive_perception(room, exclude=caller)

        if dc <= 0:
            # Empty room — auto-succeed
            caller.add_condition(Condition.HIDDEN)
            return

        # Stealth roll
        from utils.dice_roller import dice
        stealth_bonus = caller.effective_stealth_bonus
        has_adv = getattr(caller.db, "non_combat_advantage", False)
        has_dis = getattr(caller.db, "non_combat_disadvantage", False)
        roll = dice.roll_with_advantage_or_disadvantage(advantage=has_adv, disadvantage=has_dis)
        caller.db.non_combat_advantage = False
        caller.db.non_combat_disadvantage = False
        total = roll + stealth_bonus

        if total >= dc:
            caller.add_condition(Condition.HIDDEN)
            caller.msg(
                f"|g(Stealth: {roll} + {stealth_bonus} = {total} vs DC {dc})|n"
            )
        else:
            caller.msg(
                f"You look for a place to hide but can't find adequate cover. "
                f"(Stealth: {roll} + {stealth_bonus} = {total} vs DC {dc})"
            )

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
