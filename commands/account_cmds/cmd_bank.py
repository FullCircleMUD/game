"""
Account-level bank display — shows everything in the player's AccountBank.

Available from the OOC menu (account-level command). Shows all assets
that could be exported to the player's personal wallet.

Usage:
    bank
"""

from evennia import Command
from django.conf import settings

from blockchain.xrpl.currency_cache import get_resource_type
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
from typeclasses.items.base_nft_item import BaseNFTItem

GOLD = settings.GOLD_DISPLAY


class CmdBank(Command):
    """
    View your in-game bank account.

    Shows all assets stored in your account bank, including gold,
    resources, and NFT items. These are the assets available for
    export to your personal wallet.

    Usage:
        bank
    """

    key = "bank"
    locks = "cmd:is_ooc()"
    help_category = "Bank"

    def func(self):
        account = self.caller

        bank = ensure_bank(account)

        # --- Collect bank contents ---
        gold = bank.get_gold()
        resources = bank.db.resources or {}
        nft_items = [obj for obj in bank.contents if isinstance(obj, BaseNFTItem)]

        has_anything = gold > 0 or any(v > 0 for v in resources.values()) or nft_items

        if not has_anything:
            account.msg(
                "|c--- Account Bank ---|n\n"
                "Your bank is empty.\n"
                "|c--- End of Bank ---|n"
            )
            return

        # --- Build display ---
        lines = ["|c--- Account Bank ---|n"]

        # Gold
        if gold > 0:
            lines.append(f"  {GOLD['name']}: {gold} {GOLD['unit']}")

        # Resources
        for resource_id in sorted(resources.keys()):
            amount = resources[resource_id]
            if amount <= 0:
                continue
            rt = get_resource_type(resource_id)
            if rt:
                lines.append(f"  {rt['name']}: {amount} {rt['unit']}")
            else:
                lines.append(f"  Resource {resource_id}: {amount}")

        # NFT items
        if nft_items:
            lines.append("")
            lines.append("|wItems:|n")
            for obj in nft_items:
                token_label = f" |w[#{obj.id}]|n" if obj.token_id else ""
                condition = (
                    obj.get_condition_label()
                    if hasattr(obj, "get_condition_label")
                    else ""
                )
                cond_suffix = f"  ({condition})" if condition else ""
                lines.append(f"  {obj.key}{token_label}{cond_suffix}")

        lines.append("")
        lines.append(
            "|yItems carried by your characters are not shown here.|n\n"
            "|yTo export an item from a character, deposit it at a bank first.|n"
        )
        lines.append("")
        lines.append(
            "Use |wexport <token_id>|n or |wexport gold 50|n"
            " to move assets to your wallet."
        )
        lines.append("|c--- End of Bank ---|n")
        account.msg("\n".join(lines))
