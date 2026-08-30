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
from utils.item_parse import ALL, split_quantity
from utils.targeting.helpers import all_inventory, resolve_target

GOLD = settings.GOLD_DISPLAY


def _amount(quantity):
    """Turn a parsed quantity into the amount the fungible handlers want.

    They read ``None`` as "all of it", so ``ALL`` maps to ``None`` and a
    missing quantity maps to one.
    """
    if quantity is ALL:
        return None
    return 1 if quantity is None else quantity


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
    aliases = []
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
        split = split_quantity(self.args)

        if split is None or split.subject is None:
            caller.msg("Deposit what? Try: deposit sword, deposit gold, deposit 5 wheat")
            return
        quantity, subject = split

        # An item ID is a name the split cannot read, so it is checked
        # before the name goes anywhere near the inventory search.
        if subject.startswith("#") and subject[1:].isdigit():
            self._deposit_nft(caller, bank, int(subject[1:]))
            return
        if subject.isdigit():
            self._deposit_nft(caller, bank, int(subject))
            return

        kind, payload = all_inventory(caller, subject)

        if kind == "gold":
            self._deposit_gold(caller, bank, _amount(quantity))
        elif kind == "resource":
            self._deposit_resource(
                caller, bank, _amount(quantity),
                payload["resource_id"], payload,
            )
        elif kind == "ambiguous":
            caller.msg(
                "Did you mean "
                + " or ".join(info["name"] for info in payload)
                + "?"
            )
        elif kind == "items":
            self._deposit_items(caller, bank, subject, payload, quantity)
        else:
            self._no_match(caller, subject)

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

    def _deposit_items(self, caller, bank, subject, matches, quantity):
        """Bank the one item the player meant, or say why there isn't one.

        Identical copies are not an ambiguous request — bank one of
        them. Whether an item is bankable is judged per item, so a
        non-NFT match never blocks an NFT one with the same name.
        """
        if quantity is not None:
            caller.msg(
                f"You can't deposit {quantity} of those — only gold and "
                f"resources come in amounts."
            )
            return

        if len({obj.key.lower() for obj in matches}) > 1:
            # Distinct names — let Evennia render its multimatch list.
            caller.search(subject, candidates=matches)
            return

        obj = next((o for o in matches if isinstance(o, BaseNFTItem)), None)
        if obj is None:
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

    def _no_match(self, caller, subject):
        """Nothing carried answers to that name. Say the most useful thing.

        Worn gear is not a candidate, so it surfaces only here — and
        only to explain why the thing the player can see on themselves
        was not banked.
        """
        worn, _ = resolve_target(caller, subject, "items_equipped")
        worn = worn[0] if worn else None
        if worn:
            caller.msg(f"You must remove {worn.key} first.")
            return
        caller.msg(f"You aren't carrying '{subject}'.")

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
