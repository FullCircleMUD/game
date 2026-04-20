"""
Bank withdraw command — move items from AccountBank to character inventory.

Available only in bank rooms (added via CmdSetBank on RoomBank).

Usage:
    withdraw <item>                — withdraw an item by name (fuzzy match)
    withdraw #<id>                 — withdraw an NFT by token ID
    withdraw <amount> <fungible>   — withdraw a specific amount
    withdraw all <fungible>        — withdraw all of a fungible
    withdraw <fungible>            — withdraw 1 of a fungible (default)

Aliases: with

Examples:
    with sword        — withdraw an item named "sword"
    with #42          — withdraw NFT #42
    with gold         — withdraw 1 gold
    with 12 gold      — withdraw 12 gold
    with all gold     — withdraw all gold
    with 5 wheat      — withdraw 5 wheat
"""

from evennia import Command
from django.conf import settings

from commands.command import FCMCommandMixin
from commands.room_specific_cmds.bank.cmd_balance import ensure_bank
from typeclasses.items.base_nft_item import BaseNFTItem
from utils.item_parse import parse_item_args
from utils.weight_check import (
    check_can_carry, get_item_weight, get_gold_weight, get_resource_weight,
)

GOLD = settings.GOLD_DISPLAY


class CmdWithdraw(FCMCommandMixin, Command):
    """
    Withdraw items from your bank.

    Usage:
        withdraw <item>
        withdraw #<id>
        withdraw <amount> <fungible>
        withdraw all <fungible>
        withdraw <fungible>
    """

    key = "withdraw"
    aliases = []
    locks = "cmd:all()"
    help_category = "Bank"

    def func(self):
        caller = self.caller
        account = caller.account

        if not self.args:
            caller.msg("Usage: withdraw <item> | withdraw <amount> <fungible>")
            return

        if not account:
            caller.msg("You need to be logged in to withdraw.")
            return

        bank = ensure_bank(account)
        parsed = parse_item_args(self.args)

        if parsed is None:
            caller.msg("Withdraw what? Try: withdraw sword, withdraw gold, withdraw 5 wheat")
            return

        if parsed.type == "token_id":
            self._withdraw_nft(caller, bank, parsed.token_id)
        elif parsed.type == "gold":
            self._withdraw_gold(caller, bank, parsed.amount)
        elif parsed.type == "resource":
            self._withdraw_resource(
                caller, bank, parsed.amount, parsed.resource_id, parsed.resource_info
            )
        elif parsed.type == "item":
            self._withdraw_item(caller, bank, parsed.search_term)
        else:  # type == "all"
            caller.msg("Withdraw what? Try: withdraw all gold, withdraw all wheat")

    def _withdraw_nft(self, caller, bank, item_id):
        """Withdraw an NFT from the bank by item ID."""
        nft_item = None
        for obj in bank.contents:
            if isinstance(obj, BaseNFTItem) and obj.id == item_id:
                nft_item = obj
                break

        if nft_item is None:
            caller.msg(f"No item with ID #{item_id} in your bank.")
            return

        ok, msg = check_can_carry(caller, get_item_weight(nft_item))
        if not ok:
            caller.msg(msg)
            return

        if nft_item.move_to(caller, quiet=True, move_type="give"):
            caller.msg(f"You withdraw {nft_item.key}.")
            caller.location.msg_contents(
                "$You() $conj(make) a bank transaction.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg("Something went wrong withdrawing that item.")

    def _withdraw_item(self, caller, bank, search_term):
        """Withdraw an item from the bank by name (fuzzy match)."""
        obj = caller.search(
            search_term,
            candidates=list(bank.contents),
            nofound_string=f"No item matching '{search_term}' in your bank.",
        )
        if not obj:
            return

        if not isinstance(obj, BaseNFTItem):
            caller.msg("That item cannot be withdrawn.")
            return

        ok, msg = check_can_carry(caller, get_item_weight(obj))
        if not ok:
            caller.msg(msg)
            return

        if obj.move_to(caller, quiet=True, move_type="give"):
            caller.msg(f"You withdraw {obj.key}.")
            caller.location.msg_contents(
                "$You() $conj(make) a bank transaction.",
                from_obj=caller,
                exclude=[caller],
            )
        else:
            caller.msg("Something went wrong withdrawing that item.")

    def _withdraw_gold(self, caller, bank, amount):
        """Withdraw gold from the bank."""
        available = bank.get_gold()

        if available <= 0:
            caller.msg("You don't have any gold in your bank.")
            return

        if amount is None:
            amount = available  # "all"

        if amount <= 0:
            caller.msg("Amount must be positive.")
            return

        if available < amount:
            caller.msg(
                f"Your bank only has {available} {GOLD['unit']} of {GOLD['name']}."
            )
            return

        ok, msg = check_can_carry(caller, get_gold_weight(amount))
        if not ok:
            caller.msg(msg)
            return

        bank.transfer_gold_to(caller, amount)
        caller.msg(f"You withdraw {amount} {GOLD['unit']} of {GOLD['name']}.")
        caller.location.msg_contents(
            "$You() $conj(make) a bank transaction.",
            from_obj=caller,
            exclude=[caller],
        )

    def _withdraw_resource(self, caller, bank, amount, resource_id, resource_info):
        """Withdraw a resource from the bank."""
        available = bank.get_resource(resource_id)

        if available <= 0:
            caller.msg(
                f"You don't have any {resource_info['name']} in your bank."
            )
            return

        if amount is None:
            amount = available  # "all"

        if amount <= 0:
            caller.msg("Amount must be positive.")
            return

        if available < amount:
            caller.msg(
                f"Your bank only has {available} {resource_info['unit']}"
                f" of {resource_info['name']}."
            )
            return

        ok, msg = check_can_carry(caller, get_resource_weight(resource_id, amount))
        if not ok:
            caller.msg(msg)
            return

        bank.transfer_resource_to(caller, resource_id, amount)
        caller.msg(
            f"You withdraw {amount} {resource_info['unit']}"
            f" of {resource_info['name']}."
        )
        caller.location.msg_contents(
            "$You() $conj(make) a bank transaction.",
            from_obj=caller,
            exclude=[caller],
        )
