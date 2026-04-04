"""
CmdJoin — join an ally's fight by attacking their target.

Convenience command: instead of identifying the enemy by name, just
type `join <ally>` to attack whoever they're fighting.

Usage:
    join <ally>
"""

from evennia import Command

from commands.command import FCMCommandMixin
from combat.combat_utils import enter_combat
from enums.condition import Condition


class CmdJoin(FCMCommandMixin, Command):
    """
    Join an ally's fight.

    Usage:
        join <ally>

    Enter combat against whoever your ally is currently fighting.
    This is a shortcut for 'attack <their target>'.
    """

    key = "join"
    help_category = "Combat"
    locks = "cmd:all()"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Join who? Usage: join <ally>")
            return

        ally = caller.search(self.args.strip())
        if not ally:
            return

        if ally == caller:
            caller.msg("You can't join your own fight.")
            return

        # Ally must be in combat
        ally_handler = ally.scripts.get("combat_handler")
        if not ally_handler:
            caller.msg(f"{ally.key} is not in combat.")
            return

        # Find who the ally is fighting
        target = ally.ndb.combat_target
        if not target or not hasattr(target, "hp") or target.hp <= 0:
            caller.msg(f"You can't tell who {ally.key} is fighting.")
            return

        # Target must still be in the room
        if target.location != caller.location:
            caller.msg(f"{target.key} is no longer here.")
            return

        # Already fighting that target?
        caller_handler = caller.scripts.get("combat_handler")
        if caller_handler and caller.ndb.combat_target == target:
            caller.msg(f"You're already fighting {target.key}!")
            return

        # Break stealth if hidden/invisible
        if hasattr(caller, "has_condition"):
            if caller.has_condition(Condition.HIDDEN):
                caller.remove_condition(Condition.HIDDEN)
            if caller.has_condition(Condition.INVISIBLE):
                caller.break_invisibility()

        caller.msg(f"|rYou join {ally.key}'s fight against {target.key}!|n")

        # Enter combat — free instigator attack + initiative staggering
        if not enter_combat(caller, target, instigator=caller):
            return
        if caller.location:
            caller.location.msg_contents(
                f"|r{caller.key} joins the fight against {target.key}!|n",
                exclude=[caller],
            )
