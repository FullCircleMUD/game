"""
Hunger command — check your current hunger level.

Usage:
    hunger
"""

from evennia import Command


class CmdHunger(Command):
    """
    Check your current hunger level.

    Usage:
        hunger
    """

    key = "hunger"
    locks = "cmd:all()"
    help_category = "Character"
    arg_regex = r"\s|$"

    def func(self):
        self.msg(self.caller.hunger_level.get_hunger_message())
