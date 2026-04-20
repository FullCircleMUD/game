"""
CMD_NOMATCH override — replaces Evennia's default "Command 'x' is not
available. Maybe you meant..." with a terse "Huh?!?".
"""

from evennia import Command
from evennia.commands.cmdhandler import CMD_NOMATCH


class CmdNoMatch(Command):
    """Catches any input that doesn't match a known command."""

    key = CMD_NOMATCH
    locks = "cmd:all()"

    def func(self):
        self.caller.msg("Huh?!?")
