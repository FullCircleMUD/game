"""
Hunger command — check your current hunger level.

Usage:
    hunger
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdHunger(FCMCommandMixin, Command):
    """
    Check your current hunger level.

    Usage:
        hunger
    """

    key = "hunger"
    locks = "cmd:all()"
    help_category = "Character"
    arg_regex = r"\s|$"
    allow_while_sleeping = True

    def func(self):
        self.msg(self.caller.hunger_level.get_hunger_message())
