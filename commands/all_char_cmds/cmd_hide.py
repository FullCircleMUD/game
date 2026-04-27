"""
Hide command — attempt to become hidden in the current room.

Available to all characters. Contested check: d20 + effective stealth
bonus vs best passive perception (10 + effective perception bonus) in
the room. Binary outcome — hidden from everyone or nobody.

Unskilled characters can attempt to hide but suffer a -2 penalty
from their UNSKILLED mastery bonus, making success unlikely against
decent perceivers.

Moving while HIDDEN automatically triggers a new stealth check against
perceivers in the destination room (handled in character.at_post_move).

Usage:
    hide
"""

from evennia import Command

from commands.command import FCMCommandMixin
from enums.condition import Condition


def best_passive_perception(room, exclude=None):
    """
    Return the highest passive perception DC among characters in the room.

    Passive perception = 10 + effective_perception_bonus.
    Returns 0 if no valid perceivers (empty room = auto-succeed).

    Args:
        exclude: a single object or a set/list of objects to skip.
    """
    if exclude is None:
        exclude_set = set()
    elif isinstance(exclude, (set, list, tuple)):
        exclude_set = set(exclude)
    else:
        exclude_set = {exclude}

    best = 0
    for obj in room.contents:
        if obj in exclude_set:
            continue
        if not hasattr(obj, "effective_perception_bonus"):
            continue
        score = 10 + obj.effective_perception_bonus
        if score > best:
            best = score
    return best


class CmdHide(FCMCommandMixin, Command):
    """
    Attempt to hide in the current room.

    Usage:
        hide

    Rolls your stealth (d20 + stealth bonus) against the best
    passive perception in the room. If successful, you become
    hidden — invisible to other characters until you take an
    aggressive or noisy action, or are found by a search.

    Anyone can attempt to hide, but characters without stealth
    training suffer a penalty. Skilled rogues hide far more
    effectively.

    Moving while hidden automatically tests your stealth against
    perceivers in each new room.
    """

    key = "hide"
    aliases = []
    locks = "cmd:all()"
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

        # Best passive perception in room
        dc = best_passive_perception(room, exclude=caller)

        if dc <= 0:
            # Empty room — auto-succeed
            caller.add_condition(Condition.HIDDEN)
            return

        # Stealth roll — racial advantage (e.g. halfling) is permanent
        from utils.dice_roller import dice
        stealth_bonus = caller.effective_stealth_bonus
        has_adv = getattr(caller.db, "non_combat_advantage", False)
        race = getattr(caller, "race", None)
        if race:
            from typeclasses.actors.races import get_race
            race_data = get_race(race)
            if race_data and "stealth" in getattr(race_data, "racial_skill_advantages", frozenset()):
                has_adv = True
        has_dis = getattr(caller.db, "non_combat_disadvantage", False)
        roll = dice.roll_with_advantage_or_disadvantage(advantage=has_adv, disadvantage=has_dis)
        caller.db.non_combat_advantage = False
        caller.db.non_combat_disadvantage = False
        total = roll + stealth_bonus

        if total >= dc:
            caller.add_condition(Condition.HIDDEN)
            caller.msg("|gYou slip into the shadows, unseen.|n")
            from utils.skill_xp import award_skill_xp
            award_skill_xp(caller, dc)
        else:
            caller.msg(
                "You look for a place to hide but can't find adequate cover."
            )
