"""
Import command — bring assets from the player's XRPL wallet into the game.

Account-level (OOC) command. Imports go into the account bank.

Usage:
    import gold [amount|all]       — import gold from wallet
    import <resource> [amount|all] — import a resource from wallet
    import nft                     — list wallet NFTs with numbers
    import nft <N>                 — import Nth NFT from wallet listing

Fungible imports: player signs Payment to vault via Xaman (1 signature).
NFT imports: player creates sell offer via Xaman → vault accepts (1 signature).

All XRPL/Xaman calls run in worker threads (deferToThread) so the
reactor stays responsive for other players.
"""

from decimal import Decimal

from django.conf import settings
from evennia import Command
from evennia.utils import delay
from evennia.utils.evmenu import get_input
from twisted.internet import threads

from commands.room_specific_cmds.bank._bank_parse import parse_bank_args
from subscriptions.utils import is_subscribed, has_paid

MAX_POLL_ATTEMPTS = 60  # 2 seconds × 60 = 2-minute timeout


class CmdImport(Command):
    """
    Import assets from your XRPL wallet into the game.

    Usage:
        import gold [amount|all]
        import <resource> [amount|all]
        import nft
        import nft <N>

    Assets are placed in your account bank.
    Use 'withdraw' at a bank room to move them to a character.
    """

    key = "import"
    locks = "cmd:is_ooc()"
    help_category = "Bank"

    def func(self):
        account = self.caller

        if not settings.XRPL_IMPORT_EXPORT_ENABLED:
            account.msg("|yImport/export is currently disabled.|n")
            return

        if not is_subscribed(account):
            account.msg(
                "|rYour subscription has expired.|n\n"
                "Use |wsubscribe|n to renew."
            )
            return

        if not has_paid(account):
            account.msg(
                "|rImport is not available during the free trial.|n\n"
                "Use |wsubscribe|n to activate your subscription."
            )
            return

        # Bot accounts are always blocked from import/export
        bot_names = getattr(settings, "BOT_ACCOUNT_USERNAMES", [])
        bot_wallets = set(getattr(settings, "BOT_WALLET_ADDRESSES", {}).values())
        wallet = account.attributes.get("wallet_address")
        if account.key in bot_names or (wallet and wallet in bot_wallets):
            account.msg("|rBot accounts cannot import assets.|n")
            return

        wallet = account.wallet_address
        if not wallet:
            account.msg("|rNo wallet linked to your account.|n")
            return

        bank = account.db.bank
        if not bank:
            account.msg("|rNo account bank found.|n")
            return

        # Ensure bank wallet stays in sync with account
        if bank.wallet_address != wallet:
            bank.wallet_address = wallet

        if not self.args:
            account.msg(
                "Usage: import gold [amount] | import <resource> [amount]"
                " | import nft [N]"
            )
            return

        # Check for NFT commands first (parse_bank_args doesn't handle "nft")
        parts = self.args.strip().split()
        if parts[0].lower() == "nft":
            _import_nft(account, bank, wallet, parts[1:])
            return

        parsed = parse_bank_args(self.args)
        if parsed is None:
            account.msg(
                "Import what? Use exact names or 'nft'.\n"
                "  import gold 50  |  import wheat 3  |  import nft 1"
            )
            return

        parsed_type = parsed[0]

        if parsed_type == "nft":
            account.msg(
                "Use |wimport nft|n to see your wallet NFTs, then"
                " |wimport nft <N>|n to import by number."
            )
            return
        elif parsed_type == "gold":
            _import_gold(account, bank, wallet, parsed[1])
        else:  # resource
            _import_resource(
                account, bank, wallet, parsed[1], parsed[2], parsed[3]
            )


# ================================================================== #
#  Fungible: Gold
# ================================================================== #

def _import_gold(account, bank, wallet, amount):
    """Start gold import — query wallet balance in worker thread."""
    account.msg("|cQuerying wallet...|n")
    d = threads.deferToThread(_get_wallet_balances, wallet)
    d.addCallback(
        lambda balances: _on_gold_balances(account, bank, wallet, amount, balances)
    )
    d.addErrback(
        lambda f: _msg(account, "|rCould not query XRPL. Try again later.|n")
    )


def _on_gold_balances(account, bank, wallet, amount, balances):
    """Reactor thread — validate gold balance and prompt for confirmation."""
    if not _connected(account):
        return

    gold_code = settings.XRPL_GOLD_CURRENCY_CODE
    wallet_gold = balances.get(gold_code, Decimal("0"))

    if wallet_gold <= 0:
        account.msg("Your wallet has no gold to import.")
        return

    if amount is None:
        amount = int(wallet_gold)  # "all"

    if amount <= 0:
        account.msg("Amount must be positive.")
        return

    if wallet_gold < amount:
        account.msg(f"Your wallet only has {wallet_gold} gold.")
        return

    get_input(
        account,
        f"\n|c--- Import Gold ---|n"
        f"\nBring |w{amount} gold|n from your wallet into the game?"
        f"\nThis requires signing one transaction in Xaman."
        f"\n\n[Y]/N? ",
        lambda caller, prompt, result: _on_gold_import_confirmed(
            caller, bank, wallet, amount, result,
        ),
    )


def _on_gold_import_confirmed(account, bank, wallet, amount, answer):
    """get_input callback — user confirmed gold import."""
    if answer.strip().lower() in ("n", "no"):
        account.msg("Import cancelled.")
        return False

    gold_code = settings.XRPL_GOLD_CURRENCY_CODE
    from blockchain.xrpl.xrpl_tx import encode_currency_hex
    from blockchain.xrpl.memo import build_memo, MEMO_IMPORT
    hex_code = encode_currency_hex(gold_code)
    memos = [build_memo(MEMO_IMPORT, {
        "type": "gold", "currency": gold_code, "amount": str(amount),
    })]

    account.msg("|cCreating payment request...|n")
    d = threads.deferToThread(
        _create_payment_payload, hex_code, amount, memos,
    )
    d.addCallback(
        lambda payload: _on_fungible_payment_payload(
            account, bank, "gold", gold_code, None, amount, payload,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError contacting Xaman: {f.getErrorMessage()}|n")
    )
    return False


# ================================================================== #
#  Fungible: Resources
# ================================================================== #

def _import_resource(account, bank, wallet, amount, resource_id,
                     resource_info):
    """Start resource import — query wallet balance in worker thread."""
    from blockchain.xrpl.currency_cache import get_currency_code

    currency_code = get_currency_code(resource_id)
    if not currency_code:
        account.msg(
            f"|rNo currency code found for {resource_info['name']}.|n"
        )
        return

    account.msg("|cQuerying wallet...|n")
    d = threads.deferToThread(_get_wallet_balances, wallet)
    d.addCallback(
        lambda balances: _on_resource_balances(
            account, bank, wallet, amount, resource_id, resource_info,
            currency_code, balances,
        )
    )
    d.addErrback(
        lambda f: _msg(account, "|rCould not query XRPL. Try again later.|n")
    )


def _on_resource_balances(account, bank, wallet, amount, resource_id,
                          resource_info, currency_code, balances):
    """Reactor thread — validate resource balance and prompt."""
    if not _connected(account):
        return

    wallet_amount = balances.get(currency_code, Decimal("0"))
    name = resource_info["name"]
    unit = resource_info["unit"]

    if wallet_amount <= 0:
        account.msg(f"Your wallet has no {name} to import.")
        return

    if amount is None:
        amount = int(wallet_amount)  # "all"

    if amount <= 0:
        account.msg("Amount must be positive.")
        return

    if wallet_amount < amount:
        account.msg(
            f"Your wallet only has {wallet_amount} {unit} of {name}."
        )
        return

    get_input(
        account,
        f"\n|c--- Import {name} ---|n"
        f"\nBring |w{amount} {unit}|n of {name} into the game?"
        f"\nThis requires signing one transaction in Xaman."
        f"\n\n[Y]/N? ",
        lambda caller, prompt, result: _on_resource_import_confirmed(
            caller, bank, wallet, amount, resource_id, resource_info,
            currency_code, result,
        ),
    )


def _on_resource_import_confirmed(account, bank, wallet, amount, resource_id,
                                  resource_info, currency_code, answer):
    """get_input callback — user confirmed resource import."""
    if answer.strip().lower() in ("n", "no"):
        account.msg("Import cancelled.")
        return False

    from blockchain.xrpl.xrpl_tx import encode_currency_hex
    from blockchain.xrpl.memo import build_memo, MEMO_IMPORT
    hex_code = encode_currency_hex(currency_code)
    memos = [build_memo(MEMO_IMPORT, {
        "type": "resource", "currency": currency_code, "amount": str(amount),
    })]

    account.msg(f"|cCreating payment request...|n")
    d = threads.deferToThread(
        _create_payment_payload, hex_code, amount, memos,
    )
    d.addCallback(
        lambda payload: _on_fungible_payment_payload(
            account, bank, "resource", currency_code, resource_id, amount,
            payload,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError contacting Xaman: {f.getErrorMessage()}|n")
    )
    return False


# ================================================================== #
#  Shared fungible: payload → polling → verification
# ================================================================== #

def _on_fungible_payment_payload(account, bank, asset_type, currency_code,
                                 resource_id, amount, payload):
    """Reactor thread — show deeplink and start polling."""
    if not _connected(account):
        return

    uuid = payload["uuid"]
    deeplink = payload["deeplink"]

    account.msg("|c--- Sign Payment ---|n")
    account.msg(f"\nOpen this link to sign in Xaman:")
    account.msg(f"|w{deeplink}|n")
    account.msg(f"\nWaiting for you to sign... (2 minute timeout)")

    _poll_xaman_fungible_import(
        account, bank, asset_type, currency_code, resource_id, amount,
        uuid, attempt=0,
    )


def _poll_xaman_fungible_import(account, bank, asset_type, currency_code,
                                resource_id, amount, uuid, attempt):
    """Poll Xaman for fungible payment signing result (non-blocking)."""
    if attempt >= MAX_POLL_ATTEMPTS:
        _msg(account, "|r--- Timed out waiting for Xaman signing ---|n")
        return

    d = threads.deferToThread(_get_payload_status, uuid)
    d.addCallback(
        lambda status: _on_fungible_poll_result(
            account, bank, asset_type, currency_code, resource_id, amount,
            uuid, attempt, status,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError polling Xaman: {f.getErrorMessage()}|n")
    )


def _on_fungible_poll_result(account, bank, asset_type, currency_code,
                             resource_id, amount, uuid, attempt, status):
    """Reactor thread — process fungible import poll result."""
    if status["expired"]:
        _msg(account, "|r--- Xaman request expired ---|n")
        return

    if not status["resolved"]:
        delay(2, _poll_xaman_fungible_import, account, bank, asset_type,
              currency_code, resource_id, amount, uuid, attempt + 1)
        return

    if not status["signed"]:
        _msg(account, "|r--- Payment was rejected ---|n")
        return

    tx_hash = status.get("tx_hash")

    # Verify on-chain in worker thread
    from blockchain.xrpl.xrpl_tx import encode_currency_hex
    hex_code = encode_currency_hex(currency_code)

    account.msg("|cVerifying on-chain payment...|n")
    d = threads.deferToThread(
        _verify_fungible_payment, tx_hash, hex_code, amount,
    )
    d.addCallback(
        lambda verified_amount: _on_fungible_verified(
            account, bank, asset_type, currency_code, resource_id,
            tx_hash, verified_amount,
        )
    )
    d.addErrback(
        lambda f: _on_verify_error(account, f, tx_hash)
    )


def _on_fungible_verified(account, bank, asset_type, currency_code,
                          resource_id, tx_hash, verified_amount):
    """Reactor thread — verification passed, credit the bank."""
    if not _connected(account):
        return

    verified_int = int(verified_amount)

    try:
        if asset_type == "gold":
            bank.deposit_gold_from_chain(verified_int, tx_hash)
        else:
            bank.deposit_resource_from_chain(resource_id, verified_int, tx_hash)
    except ValueError as e:
        _msg(account, f"|rDB error after payment: {e}|n")
        _msg(account, f"|yTx hash: {tx_hash} — contact an admin.|n")
        return

    if asset_type == "gold":
        account.msg(
            f"|g--- Import Complete ---|n"
            f"\n|w{verified_int} gold|n added to your account bank."
            f"\nTx: |w{tx_hash}|n"
        )
    else:
        from blockchain.xrpl.currency_cache import get_resource_type
        info = get_resource_type(resource_id) or {}
        name = info.get("name", currency_code)
        unit = info.get("unit", "")
        account.msg(
            f"|g--- Import Complete ---|n"
            f"\n|w{verified_int} {unit}|n of {name} added to your account bank."
            f"\nTx: |w{tx_hash}|n"
        )


def _on_verify_error(account, failure, tx_hash):
    """Reactor thread — on-chain verification failed."""
    if not _connected(account):
        return
    account.msg("|r--- On-chain verification failed ---|n")
    account.msg(f"|r{failure.getErrorMessage()}|n")
    account.msg(f"|yTx hash: {tx_hash} — contact an admin.|n")


# ================================================================== #
#  NFT
# ================================================================== #

def _import_nft(account, bank, wallet, nft_args):
    """Start NFT import — query wallet in worker thread."""
    account.msg("|cQuerying wallet...|n")
    d = threads.deferToThread(_get_wallet_nfts, wallet)
    d.addCallback(
        lambda nfts: _on_wallet_nfts(account, bank, wallet, nft_args, nfts)
    )
    d.addErrback(
        lambda f: _msg(account, "|rCould not query XRPL. Try again later.|n")
    )


def _on_wallet_nfts(account, bank, wallet, nft_args, nfts):
    """Reactor thread — display NFT list or start import flow."""
    if not _connected(account):
        return

    if not nfts:
        account.msg("Your wallet has no NFTs to import.")
        return

    # No number given — show list
    if not nft_args:
        lines = ["|c--- Wallet NFTs ---|n"]
        for i, nft in enumerate(nfts, 1):
            lines.append(f"  {i}. {nft['name']}")
        lines.append("")
        lines.append("Use |wimport nft <N>|n to import one.")
        lines.append("|c---|n")
        account.msg("\n".join(lines))
        return

    # Parse number
    try:
        selection = int(nft_args[0])
    except (ValueError, IndexError):
        account.msg(
            "Use a number: |wimport nft 1|n, |wimport nft 2|n, etc."
        )
        return

    if selection < 1 or selection > len(nfts):
        account.msg(f"Invalid selection. Choose 1-{len(nfts)}.")
        return

    selected_nft = nfts[selection - 1]
    nftoken_id = selected_nft["nftoken_id"]
    nft_name = selected_nft["name"]

    # Verify it's a known game NFT with an item type
    from blockchain.xrpl.models import NFTGameState

    try:
        game_nft = NFTGameState.objects.select_related("item_type").get(
            nftoken_id=nftoken_id,
        )
    except NFTGameState.DoesNotExist:
        account.msg(f"|r{nft_name} is not a recognised game NFT.|n")
        return

    if not game_nft.item_type:
        account.msg(
            f"|r{nft_name} has no item type assigned — cannot import.|n"
        )
        return

    get_input(
        account,
        f"\n|c--- Import NFT ---|n"
        f"\nBring |w{nft_name}|n into the game?"
        f"\nThis requires signing one transaction in Xaman."
        f"\n\n[Y]/N? ",
        lambda caller, prompt, result: _on_nft_import_confirmed(
            caller, bank, nftoken_id, nft_name, result,
        ),
    )


def _on_nft_import_confirmed(account, bank, nftoken_id, nft_name, answer):
    """get_input callback — user confirmed NFT import."""
    if answer.strip().lower() in ("n", "no"):
        account.msg("Import cancelled.")
        return False

    from blockchain.xrpl.memo import build_memo, MEMO_NFT_IMPORT
    memos = [build_memo(MEMO_NFT_IMPORT, {"nftId": nftoken_id})]
    account.msg("|cCreating sell offer request...|n")
    d = threads.deferToThread(
        _create_nft_sell_offer_payload, nftoken_id, memos,
    )
    d.addCallback(
        lambda payload: _on_nft_sell_payload(
            account, bank, nftoken_id, nft_name, payload,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError contacting Xaman: {f.getErrorMessage()}|n")
    )
    return False


def _on_nft_sell_payload(account, bank, nftoken_id, nft_name, payload):
    """Reactor thread — show deeplink and start polling."""
    if not _connected(account):
        return

    uuid = payload["uuid"]
    deeplink = payload["deeplink"]

    account.msg("|c--- Create Sell Offer ---|n")
    account.msg(f"\nOpen this link to sign in Xaman:")
    account.msg(f"|w{deeplink}|n")
    account.msg(f"\nWaiting for you to sign... (2 minute timeout)")

    _poll_xaman_nft_import(
        account, bank, nftoken_id, nft_name, uuid, attempt=0,
    )


def _poll_xaman_nft_import(account, bank, nftoken_id, nft_name, uuid,
                           attempt):
    """Poll Xaman for NFT sell offer creation result (non-blocking)."""
    if attempt >= MAX_POLL_ATTEMPTS:
        _msg(account, "|r--- Timed out waiting for Xaman signing ---|n")
        return

    d = threads.deferToThread(_get_payload_status, uuid)
    d.addCallback(
        lambda status: _on_nft_poll_result(
            account, bank, nftoken_id, nft_name, uuid, attempt, status,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError polling Xaman: {f.getErrorMessage()}|n")
    )


def _on_nft_poll_result(account, bank, nftoken_id, nft_name, uuid, attempt,
                        status):
    """Reactor thread — process NFT import poll result."""
    if status["expired"]:
        _msg(account, "|r--- Xaman request expired ---|n")
        return

    if not status["resolved"]:
        delay(2, _poll_xaman_nft_import, account, bank, nftoken_id,
              nft_name, uuid, attempt + 1)
        return

    if not status["signed"]:
        _msg(account, "|r--- NFT sell offer was rejected ---|n")
        return

    tx_hash = status.get("tx_hash")

    # Accept the offer in a worker thread (two XRPL calls: get_transaction + accept)
    from blockchain.xrpl.memo import build_memo, MEMO_NFT_IMPORT
    memos = [build_memo(MEMO_NFT_IMPORT, {"nftId": nftoken_id})]
    account.msg("|cAccepting NFT transfer...|n")
    d = threads.deferToThread(_accept_nft_import, tx_hash, memos)
    d.addCallback(
        lambda accept_tx_hash: _on_nft_accepted(
            account, bank, nftoken_id, nft_name, accept_tx_hash,
        )
    )
    d.addErrback(
        lambda f: _on_nft_accept_error(account, f, tx_hash)
    )


def _on_nft_accepted(account, bank, nftoken_id, nft_name, accept_tx_hash):
    """Reactor thread — vault accepted the offer, spawn the game item."""
    if not _connected(account):
        return

    from typeclasses.items.base_nft_item import BaseNFTItem

    try:
        obj = BaseNFTItem.spawn_into(
            nftoken_id, bank, tx_hash=accept_tx_hash,
        )
    except Exception as e:
        _msg(account, f"|rError creating game item: {e}|n")
        _msg(account, f"|yTx hash: {accept_tx_hash} — contact an admin.|n")
        return

    if obj is None:
        _msg(account, "|rCould not create game item from NFT data.|n")
        _msg(account, f"|yTx hash: {accept_tx_hash} — contact an admin.|n")
        return

    account.msg(
        f"|g--- Import Complete ---|n"
        f"\n|w{nft_name}|n has been added to your account bank."
        f"\nTx: |w{accept_tx_hash}|n"
    )


def _on_nft_accept_error(account, failure, tx_hash):
    """Reactor thread — vault failed to accept the NFT offer."""
    if not _connected(account):
        return
    account.msg(f"|rFailed to complete NFT transfer: {failure.getErrorMessage()}|n")
    account.msg(f"|yTx hash: {tx_hash} — contact an admin.|n")


# ================================================================== #
#  Worker thread helpers (no Evennia object access)
# ================================================================== #

def _get_wallet_balances(wallet):
    """Worker thread — query XRPL wallet balances."""
    from blockchain.xrpl.xrpl_tx import get_wallet_balances
    return get_wallet_balances(wallet)


def _get_wallet_nfts(wallet):
    """Worker thread — query XRPL wallet NFTs."""
    from blockchain.xrpl.xrpl_tx import get_wallet_nfts
    return get_wallet_nfts(wallet)


def _create_payment_payload(hex_code, amount, memos=None):
    """Worker thread — create Xaman payment payload."""
    from blockchain.xrpl.xaman import create_payment_payload
    return create_payment_payload(
        settings.XRPL_VAULT_ADDRESS, hex_code, amount,
        settings.XRPL_ISSUER_ADDRESS, memos=memos,
    )


def _create_nft_sell_offer_payload(nftoken_id, memos=None):
    """Worker thread — create Xaman NFT sell offer payload."""
    from blockchain.xrpl.xaman import create_nft_sell_offer_payload
    return create_nft_sell_offer_payload(
        nftoken_id, settings.XRPL_VAULT_ADDRESS, memos=memos,
    )


def _get_payload_status(uuid):
    """Worker thread — poll Xaman API."""
    from blockchain.xrpl.xaman import get_payload_status
    return get_payload_status(uuid)


def _verify_fungible_payment(tx_hash, hex_code, amount):
    """Worker thread — verify on-chain payment."""
    from blockchain.xrpl.xrpl_tx import verify_fungible_payment
    return verify_fungible_payment(
        tx_hash,
        expected_destination=settings.XRPL_VAULT_ADDRESS,
        expected_currency_hex=hex_code,
        expected_amount=amount,
        expected_issuer=settings.XRPL_ISSUER_ADDRESS,
    )


def _accept_nft_import(tx_hash, memos=None):
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

    accept_tx_hash = accept_nft_sell_offer(offer_id, memos=memos)
    return accept_tx_hash


# ================================================================== #
#  Shared helpers
# ================================================================== #

def _connected(account):
    """True if the account still has an active session."""
    return account.sessions.count() > 0


def _msg(account, text):
    """Send a message only if the account is still connected."""
    if _connected(account):
        account.msg(text)
