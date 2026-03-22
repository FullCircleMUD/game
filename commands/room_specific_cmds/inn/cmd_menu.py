"""
Menu command — display what's available at the inn.

Usage:
    menu
"""

from evennia import Command

from commands.room_specific_cmds.inn.cmd_stew import STEW_PRICE
from commands.room_specific_cmds.inn.cmd_ale import ALE_PRICE


class CmdMenu(Command):
    """
    View the inn's menu.

    Usage:
        menu
    """

    key = "menu"
    locks = "cmd:all()"
    help_category = "Inn"

    def func(self):
        lines = [
            "|c--- Inn Menu ---|n",
            f"  |wstew|n — a warm bowl of stew ({STEW_PRICE} gold)",
            f"  |wale|n  — a frothy mug of ale ({ALE_PRICE} gold)",
        ]
        self.caller.msg("\n".join(lines))
