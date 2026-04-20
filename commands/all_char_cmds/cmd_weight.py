"""
Weight command — shows how much the character is carrying vs capacity.

Usage:
    weight
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdWeight(FCMCommandMixin, Command):
    """
    Check your carrying weight.

    Usage:
        weight

    Shows how much you are currently carrying and your maximum capacity.
    """

    key = "weight"
    aliases = ()
    locks = "cmd:all()"
    help_category = "Character"
    allow_while_sleeping = True

    def func(self):
        caller = self.caller

        if not hasattr(caller, "get_encumbrance_display"):
            caller.msg("You don't have weight tracking.")
            return

        caller.msg(caller.get_encumbrance_display())
