"""
Equipment command — display all wearslots and what is equipped.

Usage:
    equipment
    eq
"""

from evennia import Command

from commands.command import FCMCommandMixin


class CmdEquipment(FCMCommandMixin, Command):
    """
    Display your equipped items.

    Usage:
        equipment
        eq

    Shows all wearslots and what is currently equipped in each.
    """

    key = "equipment"
    aliases = ["eq"]
    locks = "cmd:all()"
    help_category = "Items"
    allow_while_sleeping = True

    def func(self):
        self.caller.msg(self.caller.equipment_cmd_output(looker=self.caller))
