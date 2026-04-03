"""
Bank deposit command — move items from character inventory to AccountBank.

Available only in bank rooms (added via CmdSetBank on RoomBank).

Usage:
    deposit <item>                — deposit an item by name (fuzzy match)
    deposit #<id>                 — deposit an NFT by token ID
    deposit <amount> <fungible>   — deposit a specific amount
    deposit all <fungible>        — deposit all of a fungible
    deposit <fungible>            — deposit 1 of a fungible (default)

Aliases: dep

Examples:
    dep sword         — deposit an item named "sword"
    dep #42           — deposit NFT #42
    dep gold          — deposit 1 gold
    dep 12 gold       — deposit 12 gold
    dep all gold      — deposit all gold
    dep 5 wheat       — deposit 5 wheat
"""

from evennia import Command
from django.conf import settings

from commands.command import FCMCommandMixin
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args

GOLD = settings.GOLD_DISPLAY


class CmdDeposit(FCMCommandMixin, Command):
    """
    Deposit items into your bank.

    Usage:
        deposit <item>
        deposit #<id>
        deposit <amount> <fungible>
        deposit all <fungible>
        deposit <fungible>
    """

    key = "deposit"
    aliases = ["dep"]
    locks = "cmd:all()"
    help_category = "Bank"

    def func(self):
        caller = self.caller
        account = caller.account

        if not self.args:
            caller.msg("Usage: deposit <item> | deposit <amount> <fungible>")
            return

        if not account:
            caller.msg("You need to be logged in to deposit.")
            return

        bank = ensure_bank(account)
        parsed = parse_item_args(self.args)

        if parsed is None:
            caller.msg("Deposit what? Try: deposit sword, deposit gold, deposit 5 wheat")
            return

        if parsed.type == "token_id":
            self._deposit_nft(caller, bank, parsed.token_id)
        elif parsed.type == "gold":
            self._deposit_gold(caller, bank, parsed.amount)
        elif parsed.type == "resource":
            self._deposit_resource(
                caller, bank, parsed.amount, parsed.resource_id, parsed.resource_info
            )
        elif parsed.type == "item":
            self._deposit_item(caller, bank, parsed.search_term)
        else:  # type == "all"
            caller.msg("Deposit what? Try: deposit all gold, deposit all wheat")

    def _deposit_nft(self, caller, bank, item_id):
        """Deposit an NFT from inventory into the bank by item ID."""
        nft_item = None
        for obj in caller.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
                nft_item = obj
                break

        if nft_item is None:
            caller.msg(f"You aren't carrying an item with ID #{item_id}.")
            return

        if caller.is_worn(nft_item):
            caller.msg(f"You must remove {nft_item.key} first.")
            return

        if nft_item.move_to(bank, quiet=True, move_type="give"):
            caller.msg(f"You deposit {nft_item.key}.")
            caller.location.msg_contents(
                "$You() $conj(make) a bank transaction.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg("Something went wrong depositing that item.")

    def _deposit_item(self, caller, bank, search_term):
        """Deposit an item from inventory by name (fuzzy match)."""
        obj = caller.search(
            search_term,
            location=caller,
            nofound_string=f"You aren't carrying '{search_term}'.",
            exclude_worn=True,
        )
        if not obj:
            return

        if not isinstance(obj, BaseNFTItem):
            caller.msg("You can only deposit NFT items into the bank.")
            return

        if obj.move_to(bank, quiet=True, move_type="give"):
            caller.msg(f"You deposit {obj.key}.")
            caller.location.msg_contents(
                "$You() $conj(make) a bank transaction.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg("Something went wrong depositing that item.")

    def _deposit_gold(self, caller, bank, amount):
        """Deposit gold into the bank."""
        current = caller.get_gold()

        if current <= 0:
            caller.msg("You don't have any gold.")
            return

        if amount is None:
            amount = current  # "all"

        if amount <= 0:
            caller.msg("Amount must be positive.")
            return

        if current < amount:
            caller.msg(
                f"You only have {current} {GOLD['unit']} of {GOLD['name']}."
            )
            return

        caller.transfer_gold_to(bank, amount)
        caller.msg(f"You deposit {amount} {GOLD['unit']} of {GOLD['name']}.")
        caller.location.msg_contents(
            "$You() $conj(make) a bank transaction.",
            from_obj=caller,
            exclude=[caller],
        )

    def _deposit_resource(self, caller, bank, amount, resource_id, resource_info):
        """Deposit a resource into the bank."""
        current = caller.get_resource(resource_id)

        if current <= 0:
            caller.msg(f"You don't have any {resource_info['name']}.")
            return

        if amount is None:
            amount = current  # "all"

        if amount <= 0:
            caller.msg("Amount must be positive.")
            return

        if current < amount:
            caller.msg(
                f"You only have {current} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
            return

        caller.transfer_resource_to(bank, resource_id, amount)
        caller.msg(
            f"You deposit {amount} {resource_info['unit']}"
            f" of {resource_info['name']}."
        )
        caller.location.msg_contents(
            "$You() $conj(make) a bank transaction.",
            from_obj=caller,
            exclude=[caller],
        )
