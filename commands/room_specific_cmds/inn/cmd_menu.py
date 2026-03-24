"""
Menu command — display what's available at the inn.

Usage:
    menu
"""

from evennia import Command

from commands.room_specific_cmds.inn.cmd_ale import ALE_PRICE
from commands.room_specific_cmds.inn.cmd_stew import BREAD_RESOURCE_ID, FALLBACK_PRICE


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
        # Try to get live stew price from AMM
        stew_price_str = self._get_stew_price()

        lines = [
            "|c--- Inn Menu ---|n",
            f"  |wstew|n — a warm bowl of stew ({stew_price_str})",
            f"  |wale|n  — a frothy mug of ale ({ALE_PRICE} gold)",
        ]
        self.caller.msg("\n".join(lines))

    def _get_stew_price(self):
        """Get the current stew price from the AMM, with fallback."""
        try:
            from blockchain.xrpl.services.amm import AMMService
            price = AMMService.get_buy_price(BREAD_RESOURCE_ID, 1)
            return f"{price} gold"
        except Exception:
            return f"{FALLBACK_PRICE} gold"
