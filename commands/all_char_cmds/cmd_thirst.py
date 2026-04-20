"""
Thirst command — check your current thirst level.

Usage:
    thirst
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdThirst(FCMCommandMixin, Command):
    """
    Check your current thirst level.

    Usage:
        thirst
    """

    key = "thirst"
    locks = "cmd:all()"
    help_category = "Character"
    arg_regex = r"\s|$"
    allow_while_sleeping = True

    def func(self):
        self.msg(self.caller.thirst_level.get_thirst_message())
