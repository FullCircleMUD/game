"""
Stash command — physically hide an object or ally in the current room.

STEALTH class skill (thief, ninja, bard). The stasher rolls d20 + effective
stealth bonus; the result becomes the object's find_dc. The object becomes
hidden from room display and can only be found via the ``search`` command.

For actors (allies), the stasher's roll places them into the HIDDEN
condition. Once hidden, normal HIDDEN rules apply — the ally uses their
own stealth if they move, and all standard hidden-breaking triggers work.

Distinct from the bard's ``conceal`` (MISDIRECTION skill, magical glamour).
Stash is physical concealment — tucking something behind loose stones,
burying it under debris, etc.

Usage:
    stash <target>
"""

from enums.condition import Condition
from enums.mastery_level import MasteryLevel
from enums.skills_enum import skills
from .cmd_skill_base import CmdSkillBase


class CmdStash(CmdSkillBase):
    """
    Physically hide an object or ally in the current room.

    Usage:
        stash <object>     — hide an item on the ground
        stash <ally>       — hide an ally using your stealth

    Rolls your stealth (d20 + stealth bonus) to determine the
    difficulty of finding the stashed object, or to place an ally
    into the hidden state.

    Hidden objects can be found with the search command.
    Hidden allies follow normal hidden rules — they use their
    own stealth if they move or take action.
    """

    key = "stash"
    skill = skills.STEALTH.value
    help_category = "Stealth"

    def func(self):
        caller = self.caller
        room = caller.location

        if not room:
            caller.msg("You have nowhere to stash anything.")
            return

        if not self.args or not self.args.strip():
            caller.msg("Stash what?")
            return

        # Mastery check — UNSKILLED can't stash
        mastery_int = caller.get_skill_mastery(self.skill) if hasattr(caller, 'get_skill_mastery') else 0
        if mastery_int <= 0:
            caller.msg(
                "You have no idea how to stash things effectively. "
                "You need training in stealth before you can hide objects."
            )
            return

        # In combat — can't stash
        if caller.scripts.get("combat_handler"):
            caller.msg("You can't stash things while in combat!")
            return

        # Find the target
        target = caller.search(self.args.strip())
        if not target:
            return

        # Determine if target is an actor or an object
        from typeclasses.actors.base_actor import BaseActor
        is_actor = isinstance(target, BaseActor)

        if is_actor:
            self._stash_actor(caller, target, room)
        else:
            self._stash_object(caller, target, room)

    def _stash_actor(self, caller, target, room):
        """Hide an ally using the stasher's stealth roll."""
        # Can't stash yourself
        if target == caller:
            caller.msg("You can't stash yourself. Use |whide|n instead.")
            return

        # Target must be in the same room
        if target.location != room:
            caller.msg("They aren't here.")
            return

        # Target already hidden
        if target.has_condition(Condition.HIDDEN):
            caller.msg(f"{target.key} is already hidden.")
            return

        # Target in combat
        if target.scripts.get("combat_handler"):
            caller.msg(f"You can't stash {target.key} while they're in combat!")
            return

        # Roll stasher's stealth — this determines whether it works
        # against current room perceivers (same check as hide command)
        from commands.all_char_cmds.cmd_hide import best_passive_perception
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

        dc = best_passive_perception(room, exclude={caller, target})

        if dc <= 0 or total >= dc:
            # Success — apply HIDDEN to the target
            target.add_condition(Condition.HIDDEN)
            caller.msg(
                f"|gYou tuck {target.key} out of sight.|n "
                f"(Stealth: {roll} + {stealth_bonus} = {total} vs DC {dc})"
            )
            target.msg(f"{caller.key} hides you from view.")
            room.msg_contents(
                f"{caller.key} ushers {target.key} out of sight.",
                exclude=[caller, target],
                from_obj=caller,
            )
        else:
            caller.msg(
                f"You try to hide {target.key} but can't find adequate cover. "
                f"(Stealth: {roll} + {stealth_bonus} = {total} vs DC {dc})"
            )

    def _stash_object(self, caller, target, room):
        """Hide an object in the room."""
        # Object must be in the room (not in inventory)
        if target.location != room:
            caller.msg("You can only stash things that are in the room.")
            return

        # Must support hidden state
        if not hasattr(target, "is_hidden"):
            caller.msg("You can't stash that.")
            return

        # Already hidden
        if target.is_hidden:
            caller.msg(f"{target.key} is already hidden.")
            return

        # Roll stealth — result becomes the find_dc
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
        dc = roll + stealth_bonus

        # Hide the object
        target.is_hidden = True
        target.find_dc = dc
        target.discovered_by = set()

        caller.msg(
            f"|gYou stash {target.key} out of sight.|n "
            f"(DC {dc}: {roll} + {stealth_bonus})"
        )
        room.msg_contents(
            f"{caller.key} tucks something away.",
            exclude=[caller],
            from_obj=caller,
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
