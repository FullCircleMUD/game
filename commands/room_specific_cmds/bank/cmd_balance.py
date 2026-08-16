"""
Bank balance command — shows what's in the player's AccountBank.

Available only in bank rooms (added via CmdSetBank on RoomBank).

Usage:
    balance              — show all bank contents (gold, resources, items,
                           and world-anchored items like ships)
    bal                  — alias for balance
"""

from evennia import Command
from django.conf import settings

from commands.command import FCMCommandMixin

from blockchain.xrpl.currency_cache import get_resource_type
from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.items.untakeables.world_anchored_nft_item import WorldAnchoredNFTItem

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
        from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role

        # Defence-in-depth path. The canonical creation is in
        # typeclasses/accounts/accounts.py:at_post_login, which runs
        # on the router (every account's first login passes through
        # the router by architecture). By the time any bank command
        # can be invoked from a shard, this row already exists.
        #
        # Gated to monolith + router so a shard-side execution path
        # cannot accidentally trigger creation against the
        # tenant-column-immutability check: under the multitenant
        # auto-stamp, a row created on a shard would land
        # shard_id=<that shard's id> and the subsequent re-stamp to
        # "*" would raise NotSupportedError. Loud failure is the
        # right response — `account.db.bank is None` on a shard
        # implies an account that somehow skipped the router login
        # flow, which is a deeper bug worth surfacing.
        role = get_role()
        if role not in (ROLE_MONOLITH, ROLE_ROUTER):
            raise RuntimeError(
                f"AccountBank defence-in-depth create reached on "
                f"role={role!r} — account.db.bank should have been "
                f"set during router-side at_post_login."
            )

        bank = create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{account.key}",
            nohome=True,
        )
        # Stamp shard_id="*" so the bank is visible to every shard's
        # auto-filter scope. On the router (unscoped) the auto-stamp
        # is skipped at create time → row lands NULL → the assignment
        # below is a legitimate first-stamp, not a tenant-column
        # mutation. Skipped in monolith (no shard_id column exists).
        if role != ROLE_MONOLITH:
            bank.shard_id = "*"
            bank.save()
            bank.flush_from_cache(force=True)
        bank.wallet_address = account.attributes.get("wallet_address")
        account.db.bank = bank
    else:
        # Keep wallet in sync (covers banks created before wallet linking)
        account_wallet = account.attributes.get("wallet_address")
        if account_wallet and bank.wallet_address != account_wallet:
            bank.wallet_address = account_wallet
    return bank


def _render_item_line(obj):
    """Standard 'item key  [#id]  (condition)' rendering for bank listings."""
    token_label = f" |w[#{obj.id}]|n" if obj.token_id else ""
    condition = (
        obj.get_condition_label() if hasattr(obj, "get_condition_label") else ""
    )
    cond_suffix = f"  ({condition})" if condition else ""
    return f"  {obj.key}{token_label}{cond_suffix}"


def _render_world_anchored_line(obj):
    """Prefer get_owned_display() (e.g. ship berth info); fall back to standard."""
    if hasattr(obj, "get_owned_display"):
        return obj.get_owned_display()
    return _render_item_line(obj)


class CmdBalance(FCMCommandMixin, Command):
    """
    Check your bank balance.

    Shows gold, resources, items, and world-anchored items (ships) currently
    in your account bank. Pets are managed from a stable room, not here.

    Usage:
        balance
    """

    key = "balance"
    aliases = []
    locks = "cmd:all()"
    help_category = "Bank"

    def func(self):
        caller = self.caller
        account = caller.account

        if not account:
            caller.msg("You need to be logged in to check your balance.")
            return

        bank = ensure_bank(account)

        # --- Collect bank contents ---
        gold = bank.get_gold()
        resources = bank.db.resources or {}
        nft_items = [obj for obj in bank.contents if isinstance(obj, BaseNFTItem)]

        # Partition: regular items vs world-anchored items (ships, future
        # property). Pets are an actor class (BasePet < BaseNPC) and are not
        # BaseNFTItem instances, so they're already filtered out above —
        # they're managed via stable rooms, not bank rooms.
        takeable_items = [
            obj for obj in nft_items if not isinstance(obj, WorldAnchoredNFTItem)
        ]
        ships = [
            obj for obj in nft_items if isinstance(obj, WorldAnchoredNFTItem)
        ]

        has_anything = (
            gold > 0
            or any(v > 0 for v in resources.values())
            or takeable_items
            or ships
        )

        if not has_anything:
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
                lines.append(_render_item_line(obj))

        # World-anchored items (ships) — always shown by default
        if ships:
            lines.append("")
            lines.append("|wShips:|n")
            for obj in ships:
                lines.append(_render_world_anchored_line(obj))

        lines.append("|c--- End of Balance ---|n")
        caller.msg("\n".join(lines))
