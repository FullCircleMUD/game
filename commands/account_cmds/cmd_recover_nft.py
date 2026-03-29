"""
Superuser command to recover orphaned NFTs back to the vault.

When an NFT is on a player's wallet but has no NFTGameState row in the
DB (e.g. after a DB wipe), this command guides the player through
sending it back to the vault. Once in the vault, sync_nfts picks it up.

Usage (OOC, superuser only):
    recover_nft <wallet_address>
"""

from django.conf import settings
from evennia import Command
from evennia.utils.evtable import EvTable
from evennia.utils.utils import delay
from twisted.internet import threads


MAX_POLL_ATTEMPTS = 60  # 2 minutes at 2s intervals


class CmdRecoverNft(Command):
    """
    Recover orphaned NFTs from a player wallet back to the vault.

    Queries a wallet for NFTs that have no NFTGameState row in the DB.
    For each orphan, creates a Xaman sell offer for the player to sign,
    then the vault accepts it. After recovery, run sync_nfts.

    Usage:
        recover_nft <wallet_address>
    """

    key = "recover_nft"
    locks = "cmd:id(1) and is_ooc()"
    help_category = "Economy"

    def func(self):
        caller = self.caller

        if not self.args or not self.args.strip():
            caller.msg("Usage: recover_nft <wallet_address>")
            return

        wallet = self.args.strip()

        caller.msg(f"|cQuerying wallet {wallet} for orphaned NFTs...|n")
        d = threads.deferToThread(_find_orphans, wallet)
        d.addCallback(lambda orphans: _on_orphans_found(caller, wallet, orphans))
        d.addErrback(lambda f: caller.msg(
            f"|rError querying wallet: {f.getErrorMessage()}|n"
        ))


def _find_orphans(wallet):
    """Worker thread — query wallet NFTs and find orphans."""
    from blockchain.xrpl.xrpl_tx import _get_wallet_nfts_async
    from blockchain.xrpl.models import NFTGameState
    from blockchain.xrpl.services.chain_sync import _extract_game_id

    import asyncio
    raw_nfts = asyncio.run(
        _get_wallet_nfts_async(settings.XRPL_NETWORK_URL, wallet)
    )

    # Filter to NFTs with no DB row
    orphans = []
    for nft in raw_nfts:
        nftoken_id = nft["NFTokenID"]
        exists = NFTGameState.objects.using("xrpl").filter(
            nftoken_id=nftoken_id,
        ).exists()
        if not exists:
            game_id = _extract_game_id(nft.get("URI"))
            orphans.append({
                "nftoken_id": nftoken_id,
                "game_id": game_id,
                "taxon": nft.get("nft_taxon", 0),
            })

    return orphans


def _on_orphans_found(caller, wallet, orphans):
    """Reactor thread — display orphans and start recovery."""
    if not caller.sessions.count():
        return

    if not orphans:
        caller.msg("|gNo orphaned NFTs found — all wallet NFTs have DB rows.|n")
        return

    caller.msg(f"\n|y--- Orphaned NFTs ({len(orphans)}) ---|n")
    for i, nft in enumerate(orphans, 1):
        game_id = nft["game_id"]
        id_str = f"game_id={game_id}" if game_id else "no game_id"
        caller.msg(f"  {i}. {nft['nftoken_id'][:16]}... ({id_str})")

    caller.msg(
        f"\n|wRecovering {len(orphans)} NFT(s) to vault.|n"
        f"\nThe wallet owner must sign each transfer in Xaman."
    )

    # Process one at a time
    _recover_next(caller, wallet, orphans, 0)


def _recover_next(caller, wallet, orphans, index):
    """Process the next orphan in the list."""
    if not caller.sessions.count():
        return

    if index >= len(orphans):
        caller.msg(
            "\n|g--- Recovery Complete ---|n"
            "\nRun |wsync_nfts|n to register recovered NFTs in the DB."
        )
        return

    nft = orphans[index]
    nftoken_id = nft["nftoken_id"]
    total = len(orphans)

    caller.msg(
        f"\n|c--- Recovering NFT {index + 1}/{total} ---|n"
        f"\n{nftoken_id[:24]}..."
    )
    caller.msg("|cCreating sell offer request...|n")

    d = threads.deferToThread(_create_sell_offer_payload, nftoken_id)
    d.addCallback(
        lambda payload: _on_payload_created(
            caller, wallet, orphans, index, nftoken_id, payload,
        )
    )
    d.addErrback(
        lambda f: _on_recover_error(caller, wallet, orphans, index, f)
    )


def _create_sell_offer_payload(nftoken_id):
    """Worker thread — create Xaman NFT sell offer targeting vault."""
    from blockchain.xrpl.xaman import create_nft_sell_offer_payload
    return create_nft_sell_offer_payload(
        nftoken_id, settings.XRPL_VAULT_ADDRESS,
    )


def _on_payload_created(caller, wallet, orphans, index, nftoken_id, payload):
    """Reactor thread — show deeplink and start polling."""
    if not caller.sessions.count():
        return

    uuid = payload["uuid"]
    deeplink = payload["deeplink"]

    caller.msg(f"\nOpen this link to sign in Xaman:")
    caller.msg(f"|w{deeplink}|n")
    caller.msg(f"\nWaiting for signature... (2 minute timeout)")

    _poll_xaman(caller, wallet, orphans, index, nftoken_id, uuid, attempt=0)


def _poll_xaman(caller, wallet, orphans, index, nftoken_id, uuid, attempt):
    """Poll Xaman for sell offer signing."""
    if attempt >= MAX_POLL_ATTEMPTS:
        caller.msg("|r--- Timed out. Skipping this NFT. ---|n")
        _recover_next(caller, wallet, orphans, index + 1)
        return

    d = threads.deferToThread(_get_payload_status, uuid)
    d.addCallback(
        lambda status: _on_poll_result(
            caller, wallet, orphans, index, nftoken_id, uuid, attempt, status,
        )
    )
    d.addErrback(
        lambda f: caller.msg(f"|rPoll error: {f.getErrorMessage()}|n")
    )


def _get_payload_status(uuid):
    """Worker thread — poll Xaman."""
    from blockchain.xrpl.xaman import get_payload_status
    return get_payload_status(uuid)


def _on_poll_result(caller, wallet, orphans, index, nftoken_id, uuid,
                    attempt, status):
    """Reactor thread — process poll result."""
    if not caller.sessions.count():
        return

    if status["expired"]:
        caller.msg("|r--- Request expired. Skipping. ---|n")
        _recover_next(caller, wallet, orphans, index + 1)
        return

    if not status["resolved"]:
        delay(2, _poll_xaman, caller, wallet, orphans, index,
              nftoken_id, uuid, attempt + 1)
        return

    if not status["signed"]:
        caller.msg("|r--- Offer rejected. Skipping. ---|n")
        _recover_next(caller, wallet, orphans, index + 1)
        return

    tx_hash = status.get("tx_hash")

    # Vault accepts the offer
    caller.msg("|cAccepting NFT transfer to vault...|n")
    d = threads.deferToThread(_accept_offer, tx_hash)
    d.addCallback(
        lambda accept_hash: _on_accepted(
            caller, wallet, orphans, index, nftoken_id, accept_hash,
        )
    )
    d.addErrback(
        lambda f: _on_recover_error(caller, wallet, orphans, index, f)
    )


def _accept_offer(tx_hash):
    """Worker thread — extract offer_id and vault accepts it."""
    from blockchain.xrpl.xrpl_tx import (
        get_transaction, accept_nft_sell_offer, _extract_offer_id,
    )

    tx_result = get_transaction(tx_hash)
    meta = tx_result.get("meta") or tx_result.get("metaData") or {}
    offer_id = _extract_offer_id(meta)
    if not offer_id:
        raise ValueError(
            f"Could not extract offer ID from transaction {tx_hash}"
        )

    accept_tx_hash = accept_nft_sell_offer(offer_id)
    return accept_tx_hash


def _on_accepted(caller, wallet, orphans, index, nftoken_id, accept_hash):
    """Reactor thread — NFT recovered to vault."""
    if not caller.sessions.count():
        return

    caller.msg(
        f"|g--- NFT recovered to vault ---|n"
        f"\n{nftoken_id[:24]}..."
        f"\nTx: |w{accept_hash}|n"
    )

    _recover_next(caller, wallet, orphans, index + 1)


def _on_recover_error(caller, wallet, orphans, index, failure):
    """Reactor thread — recovery failed for one NFT, continue to next."""
    if not caller.sessions.count():
        return

    caller.msg(f"|rFailed: {failure.getErrorMessage()}|n")
    caller.msg("|ySkipping to next NFT...|n")
    _recover_next(caller, wallet, orphans, index + 1)
