"""
Bank balance command — shows what's in the player's AccountBank.

Available only in bank rooms (added via CmdSetBank on RoomBank).

Usage:
    balance              — show withdrawable items (gold, resources, takeable NFTs)
    balance all          — show everything, including untakeables in a separate section
    bal                  — alias for balance
"""

from evennia import Command
from django.conf import settings

from blockchain.xrpl.currency_cache import get_resource_type
from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.items.untakeables.untakeable_nft_item import UntakeableNFTItem

GOLD = settings.GOLD_DISPLAY


def ensure_bank(account):
    """
    Ensure the account has an AccountBank. Creates one if missing.

    The superuser account (#1) skips bank creation during initial setup
    to avoid stealing early dbref slots. This lazy-creates it on first
    bank room visit.

    Returns the AccountBank object.
    """
    bank = account.db.bank
    if bank is None:
        from evennia.utils.create import create_object
        bank = create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{account.key}",
            nohome=True,
        )
        bank.wallet_address = account.attributes.get("wallet_address")
        account.db.bank = bank
    return bank


class CmdBalance(Command):
    """
    Check your bank balance.

    Usage:
        balance          — show items available for withdrawal
        balance all      — show all items, including those not withdrawable here
    """

    key = "balance"
    aliases = ["bal"]
    locks = "cmd:all()"
    help_category = "Bank"

    def func(self):
        caller = self.caller
        account = caller.account

        if not account:
            caller.msg("You need to be logged in to check your balance.")
            return

        bank = ensure_bank(account)
        show_all = self.args.strip().lower() == "all"

        # --- Collect bank contents ---
        gold = bank.get_gold()
        resources = bank.db.resources or {}
        nft_items = [obj for obj in bank.contents if isinstance(obj, BaseNFTItem)]

        takeable_items = [obj for obj in nft_items if not isinstance(obj, UntakeableNFTItem)]
        untakeable_items = [obj for obj in nft_items if isinstance(obj, UntakeableNFTItem)]

        has_anything = gold > 0 or any(v > 0 for v in resources.values()) or takeable_items
        has_untakeables = bool(untakeable_items)

        if not has_anything and not has_untakeables:
            caller.msg("|c--- Account Balance ---|n\nYour bank is empty.")
            return

        # --- Build display ---
        lines = ["|c--- Account Balance ---|n"]

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

        # Takeable NFT items
        if takeable_items:
            lines.append("")
            lines.append("|wItems:|n")
            for obj in takeable_items:
                token_label = f" |w[NFT #{obj.token_id}]|n" if obj.token_id else ""
                condition = (
                    obj.get_condition_label()
                    if hasattr(obj, "get_condition_label")
                    else ""
                )
                cond_suffix = f"  ({condition})" if condition else ""
                lines.append(f"  {obj.key}{token_label}{cond_suffix}")

        # Untakeable items (only shown with "balance all")
        if show_all and has_untakeables:
            lines.append("")
            lines.append("|yItems that cannot be withdrawn at a bank:|n")
            for obj in untakeable_items:
                token_label = f" |w[NFT #{obj.token_id}]|n" if obj.token_id else ""
                condition = (
                    obj.get_condition_label()
                    if hasattr(obj, "get_condition_label")
                    else ""
                )
                cond_suffix = f"  ({condition})" if condition else ""
                lines.append(f"  {obj.key}{token_label}{cond_suffix}")
        elif has_untakeables:
            lines.append("")
            lines.append(
                f"|w{len(untakeable_items)}|n other item(s) in account "
                f"(use |wbalance all|n to see)."
            )

        lines.append("|c--- End of Balance ---|n")
        caller.msg("\n".join(lines))
