"""
Superuser command to sync on-chain XRPL NFTs with the game database.

Queries the vault wallet for NFTs and updates NFTGameState with real
NFToken IDs from the ledger. Idempotent — safe to run at any time.

Usage (OOC, superuser only):
    sync_nfts
"""

from evennia import Command
from twisted.internet import threads


class CmdSyncNfts(Command):
    """
    Sync on-chain XRPL NFTs with the game database.

    Queries the vault wallet and updates NFTGameState rows with
    real NFToken IDs from the ledger. Safe to run at any time.

    Usage:
        sync_nfts
    """

    key = "sync_nfts"
    aliases = []
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Blockchain"

    def func(self):
        caller = self.caller

        from evennia_shards import ROLE_MONOLITH, ROLE_ROUTER, get_role

        role = get_role()
        if role not in (ROLE_MONOLITH, ROLE_ROUTER):
            caller.msg("|rThis command can only be run OOC on the router.|n")
            return

        caller.msg("|c--- XRPL NFT Sync ---|n")
        caller.msg("Querying vault wallet on-chain...")

        d = threads.deferToThread(_run_sync)
        d.addCallback(lambda result: _on_sync_complete(caller, result))
        d.addErrback(lambda f: _on_sync_error(caller, f))


def _run_sync():
    """Worker thread — run NFT chain sync."""
    from blockchain.xrpl.services.chain_sync import sync_nfts
    return sync_nfts()


def _on_sync_complete(caller, result):
    """Reactor thread — display sync results."""
    if not caller.sessions.count():
        return

    caller.msg(f"\n|wNFTs on chain:|n {result['on_chain_count']}")
    caller.msg(f"  Updated (placeholder → real ID): {result['updated']}")
    caller.msg(f"  Created (new to DB): {result['created']}")
    caller.msg(f"  Unchanged (already synced): {result['unchanged']}")
    if result['skipped']:
        caller.msg(f"  |ySkipped (no game ID in URI):|n {result['skipped']}")

    objects_patched = result.get('objects_patched')
    if objects_patched is None:
        caller.msg(
            "  |gObject patch sweep dispatched to all shards|n "
            "(async — check the server log for per-shard counts)"
        )
    elif objects_patched:
        caller.msg(f"  |gEvennia objects patched:|n {objects_patched}")
    caller.msg("|c--- Sync Complete ---|n")


def _on_sync_error(caller, failure):
    """Reactor thread — sync failed."""
    if caller.sessions.count():
        caller.msg(f"|r--- Sync Error: {failure.getErrorMessage()} ---|n")
