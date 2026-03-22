"""
Wallet command — show game assets in the player's XRPL wallet.

Account-level (OOC) command. Queries the XRPL ledger in real time
to show fungible balances (gold + resources) and NFTs.

Usage:
    wallet
"""

from django.conf import settings
from evennia import Command
from twisted.internet import threads


class CmdWallet(Command):
    """
    View game assets in your XRPL wallet.

    Shows all game assets (gold, resources, NFTs) currently held
    on-chain. These are available for import into the game.

    Usage:
        wallet
    """

    key = "wallet"
    locks = "cmd:is_ooc()"
    help_category = "Bank"

    def func(self):
        account = self.caller
        wallet = account.wallet_address
        if not wallet:
            account.msg("|rNo wallet linked to your account.|n")
            return

        account.msg("|cReading wallet from XRPL...|n")
        d = threads.deferToThread(_fetch_wallet_data, wallet)
        d.addCallback(lambda data: _display_wallet(account, wallet, *data))
        d.addErrback(lambda f: _on_error(account))


def _fetch_wallet_data(wallet):
    """Worker thread — blocking XRPL queries run here."""
    from blockchain.xrpl.xrpl_tx import get_wallet_balances, get_wallet_nfts

    balances = get_wallet_balances(wallet)
    nfts = get_wallet_nfts(wallet)
    return (balances, nfts)


def _on_error(account):
    """Reactor thread — handle XRPL query failure."""
    if not account.sessions.count():
        return
    account.msg("|rCould not query XRPL. Try again later.|n")


def _display_wallet(account, wallet, balances, nfts):
    """Reactor thread — format and send wallet contents."""
    if not account.sessions.count():
        return

    if not balances and not nfts:
        account.msg(
            "|c--- Your Wallet ---|n"
            f"\nAddress: |w{wallet}|n"
            "\n\nYour wallet has no game assets."
            "\n|c---|n"
        )
        return

    lines = [
        "|c--- Your Wallet ---|n",
        f"Address: |w{wallet}|n",
    ]

    # -- Fungibles --
    gold_code = settings.XRPL_GOLD_CURRENCY_CODE
    gold_display = settings.GOLD_DISPLAY
    gold_balance = balances.pop(gold_code, None)

    from blockchain.xrpl.currency_cache import (
        get_resource_id, get_resource_type,
    )

    resources = []
    for code, amount in sorted(balances.items()):
        resource_id = get_resource_id(code)
        if resource_id is not None:
            info = get_resource_type(resource_id)
            if info:
                resources.append((info["name"], info["unit"], amount))
                continue
        resources.append((code, "", amount))

    if gold_balance is not None or resources:
        lines.append("")
        lines.append("|wFungibles:|n")
        if gold_balance is not None:
            lines.append(
                f"  {gold_display['name']}: {gold_balance}"
                f" {gold_display['unit']}"
            )
        for name, unit, amount in resources:
            if unit:
                lines.append(f"  {name}: {amount} {unit}")
            else:
                lines.append(f"  {name}: {amount}")

    # -- NFTs --
    if nfts:
        lines.append("")
        lines.append("|wNFTs:|n")
        for i, nft in enumerate(nfts, 1):
            lines.append(f"  {i}. {nft['name']}")

    lines.append("")
    lines.append("Use |wimport|n to bring assets into the game.")
    lines.append("|c---|n")

    account.msg("\n".join(lines))
