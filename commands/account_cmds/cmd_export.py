"""
Export command — send assets from the account bank to the player's XRPL wallet.

Account-level (OOC) command. Only operates on items in the account bank,
not on character inventory.

Usage:
    export <token_id>            — export an NFT by token ID
    export <fungible>            — export 1 of a fungible (default)
    export <fungible> <amount>   — export a specific amount
    export <fungible> all        — export all of a fungible

Fungible exports (gold/resources): vault sends Payment to player wallet
(server-signed, no Xaman needed). Requires trust line on player wallet.

NFT exports: vault creates sell offer → player accepts via Xaman (1 signature).

All XRPL/Xaman calls run in worker threads (deferToThread) so the
reactor stays responsive for other players.
"""

from django.conf import settings
from evennia import Command
from evennia.utils import delay
from evennia.utils.evmenu import get_input
from twisted.internet import threads

from commands.room_specific_cmds.bank._bank_parse import parse_bank_args
from subscriptions.utils import has_paid

MAX_POLL_ATTEMPTS = 60  # 2 seconds × 60 = 2-minute timeout


class CmdExport(Command):
    """
    Export assets from your account bank to your XRPL wallet.

    Usage:
        export #<id>
        export <id>
        export gold [amount|all]
        export <resource> [amount|all]

    Items must be in your account bank (not on a character).
    Use 'deposit' at a bank room first if needed.
    """

    key = "export"
    aliases = ["exp"]
    locks = "cmd:is_ooc()"
    help_category = "Bank"

    def func(self):
        account = self.caller

        if not settings.XRPL_IMPORT_EXPORT_ENABLED:
            account.msg("|yImport/export is currently disabled.|n")
            return

        # Export is gated on has_paid only — once a player has ever paid for
        # a subscription they retain export access even after their sub
        # expires. The intent is to keep paid players from being trapped, while
        # blocking the free-trial recycling exploit (spam new accounts, play
        # the trial, export earnings, repeat).
        if not has_paid(account):
            account.msg(
                "|rExport is not available during the free trial.|n\n"
                "Use |wsubscribe|n to activate your subscription."
            )
            return

        # Bot accounts are always blocked from import/export
        bot_names = getattr(settings, "BOT_ACCOUNT_USERNAMES", [])
        bot_wallets = set(getattr(settings, "BOT_WALLET_ADDRESSES", {}).values())
        wallet = account.attributes.get("wallet_address")
        if account.key in bot_names or (wallet and wallet in bot_wallets):
            account.msg("|rBot accounts cannot export assets.|n")
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
                "Usage: export #<id> | export gold [amount] "
                "| export <resource> [amount]"
            )
            return

        parsed = parse_bank_args(self.args)
        if parsed is None:
            account.msg(
                "Export what? Use exact names or token IDs.\n"
                "  export #42  |  export gold 50  |  export wheat 3"
            )
            return

        parsed_type = parsed[0]

        if parsed_type == "nft":
            _export_nft(account, bank, wallet, parsed[1])
        elif parsed_type == "gold":
            _export_gold(account, bank, wallet, parsed[1])
        else:  # resource
            _export_resource(
                account, bank, wallet, parsed[1], parsed[2], parsed[3]
            )


# ================================================================== #
#  Fungible: Gold
# ================================================================== #

def _export_gold(account, bank, wallet, amount):
    """Start gold export — check trust line in worker thread."""
    current = bank.get_gold()

    if amount is None:
        amount = current  # "all"

    if amount <= 0:
        account.msg("Amount must be positive.")
        return

    if current < amount:
        account.msg(f"Your bank only has {current} gold.")
        return

    currency_code = settings.XRPL_GOLD_CURRENCY_CODE

    account.msg("|cChecking trust line...|n")
    d = threads.deferToThread(_check_trust_line, wallet, currency_code)
    d.addCallback(
        lambda has_trust: _on_gold_trust_checked(
            account, bank, wallet, amount, currency_code, has_trust,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError checking trust line: {f.getErrorMessage()}|n")
    )


def _on_gold_trust_checked(account, bank, wallet, amount, currency_code,
                           has_trust):
    """Reactor thread — trust line result for gold export."""
    if not _connected(account):
        return

    if not has_trust:
        _handle_missing_trust_line(account, wallet, currency_code)
        return

    get_input(
        account,
        f"\n|c--- Export Gold ---|n"
        f"\nSend |w{amount} gold|n to |w{wallet}|n?"
        f"\n\n[Y]/N? ",
        lambda caller, prompt, result: _on_gold_confirmed(
            caller, bank, wallet, amount, currency_code, result,
        ),
    )


def _on_gold_confirmed(account, bank, wallet, amount, currency_code, answer):
    """get_input callback — user confirmed gold export."""
    if answer.strip().lower() in ("n", "no"):
        account.msg("Export cancelled.")
        return False

    from blockchain.xrpl.memo import build_memo, MEMO_EXPORT
    memos = [build_memo(MEMO_EXPORT, {
        "type": "gold", "currency": currency_code, "amount": str(amount),
    })]
    account.msg("|cSending gold to your wallet...|n")
    d = threads.deferToThread(_send_payment, wallet, currency_code, amount, memos)
    d.addCallback(
        lambda tx_hash: _on_gold_sent(account, bank, amount, tx_hash)
    )
    d.addErrback(
        lambda f: _on_export_payment_error(account, f, "gold")
    )
    return False


def _on_gold_sent(account, bank, amount, tx_hash):
    """Reactor thread — gold payment succeeded, update game DB."""
    if not _connected(account):
        return

    try:
        bank.withdraw_gold_to_chain(amount, tx_hash)
    except ValueError as e:
        account.msg(f"|rDB error after on-chain payment: {e}|n")
        account.msg(f"|yTx hash: {tx_hash} — contact an admin.|n")
        return

    account.msg(
        f"|g--- Export Complete ---|n"
        f"\n|w{amount} gold|n sent to your wallet."
        f"\nTx: |w{tx_hash}|n"
    )


# ================================================================== #
#  Fungible: Resources
# ================================================================== #

def _export_resource(account, bank, wallet, amount, resource_id,
                     resource_info):
    """Start resource export — check trust line in worker thread."""
    current = bank.get_resource(resource_id)

    if amount is None:
        amount = current  # "all"

    if amount <= 0:
        account.msg("Amount must be positive.")
        return

    if current < amount:
        account.msg(
            f"Your bank only has {current} {resource_info['unit']}"
            f" of {resource_info['name']}."
        )
        return

    from blockchain.xrpl.currency_cache import get_currency_code
    currency_code = get_currency_code(resource_id)
    if not currency_code:
        account.msg(f"|rNo currency code found for {resource_info['name']}.|n")
        return

    account.msg("|cChecking trust line...|n")
    d = threads.deferToThread(_check_trust_line, wallet, currency_code)
    d.addCallback(
        lambda has_trust: _on_resource_trust_checked(
            account, bank, wallet, amount, resource_id, resource_info,
            currency_code, has_trust,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError checking trust line: {f.getErrorMessage()}|n")
    )


def _on_resource_trust_checked(account, bank, wallet, amount, resource_id,
                               resource_info, currency_code, has_trust):
    """Reactor thread — trust line result for resource export."""
    if not _connected(account):
        return

    if not has_trust:
        _handle_missing_trust_line(account, wallet, currency_code)
        return

    name = resource_info["name"]
    unit = resource_info["unit"]

    get_input(
        account,
        f"\n|c--- Export {name} ---|n"
        f"\nSend |w{amount} {unit}|n of {name} to |w{wallet}|n?"
        f"\n\n[Y]/N? ",
        lambda caller, prompt, result: _on_resource_confirmed(
            caller, bank, wallet, amount, resource_id, resource_info,
            currency_code, result,
        ),
    )


def _on_resource_confirmed(account, bank, wallet, amount, resource_id,
                           resource_info, currency_code, answer):
    """get_input callback — user confirmed resource export."""
    if answer.strip().lower() in ("n", "no"):
        account.msg("Export cancelled.")
        return False

    name = resource_info["name"]
    from blockchain.xrpl.memo import build_memo, MEMO_EXPORT
    memos = [build_memo(MEMO_EXPORT, {
        "type": "resource", "currency": currency_code, "amount": str(amount),
    })]
    account.msg(f"|cSending {name} to your wallet...|n")
    d = threads.deferToThread(_send_payment, wallet, currency_code, amount, memos)
    d.addCallback(
        lambda tx_hash: _on_resource_sent(
            account, bank, amount, resource_id, resource_info, tx_hash,
        )
    )
    d.addErrback(
        lambda f: _on_export_payment_error(account, f, resource_info["name"])
    )
    return False


def _on_resource_sent(account, bank, amount, resource_id, resource_info,
                      tx_hash):
    """Reactor thread — resource payment succeeded, update game DB."""
    if not _connected(account):
        return

    name = resource_info["name"]
    unit = resource_info["unit"]

    try:
        bank.withdraw_resource_to_chain(resource_id, amount, tx_hash)
    except ValueError as e:
        account.msg(f"|rDB error after on-chain payment: {e}|n")
        account.msg(f"|yTx hash: {tx_hash} — contact an admin.|n")
        return

    account.msg(
        f"|g--- Export Complete ---|n"
        f"\n|w{amount} {unit}|n of {name} sent to your wallet."
        f"\nTx: |w{tx_hash}|n"
    )


# ================================================================== #
#  NFT
# ================================================================== #

def _export_nft(account, bank, wallet, item_id):
    """Start NFT export — prompt for confirmation."""
    from typeclasses.items.base_nft_item import BaseNFTItem

    nft_item = None
    for obj in bank.contents:
        if isinstance(obj, BaseNFTItem) and obj.id == item_id:
            nft_item = obj
            break

    if nft_item is None:
        account.msg(f"No item with ID #{item_id} in your bank.")
        return

    nftoken_id = str(nft_item.token_id)

    get_input(
        account,
        f"\n|c--- Export NFT ---|n"
        f"\nSend |w{nft_item.key}|n (#{item_id}) to |w{wallet}|n?"
        f"\nThis requires signing one transaction in Xaman."
        f"\n\n[Y]/N? ",
        lambda caller, prompt, result: _on_nft_confirmed(
            caller, bank, wallet, nft_item, nftoken_id, result,
        ),
    )


def _on_nft_confirmed(account, bank, wallet, nft_item, nftoken_id, answer):
    """get_input callback — user confirmed NFT export."""
    if answer.strip().lower() in ("n", "no"):
        account.msg("Export cancelled.")
        return False

    from blockchain.xrpl.memo import build_memo, MEMO_NFT_EXPORT
    memos = [build_memo(MEMO_NFT_EXPORT, {"nftId": nftoken_id})]
    account.msg("|cCreating NFT sell offer...|n")
    d = threads.deferToThread(_create_sell_offer, nftoken_id, wallet, memos)
    d.addCallback(
        lambda data: _on_sell_offer_created(
            account, bank, nft_item, nftoken_id, data,
        )
    )
    d.addErrback(
        lambda f: _on_nft_offer_error(account, f)
    )
    return False


def _create_sell_offer(nftoken_id, wallet, memos=None):
    """Worker thread — vault creates sell offer."""
    from blockchain.xrpl.xrpl_tx import create_nft_sell_offer
    return create_nft_sell_offer(nftoken_id, wallet, memos=memos)


def _on_sell_offer_created(account, bank, nft_item, nftoken_id, data):
    """Reactor thread — sell offer created, now create Xaman accept payload."""
    if not _connected(account):
        return

    sell_tx_hash, offer_id = data

    from blockchain.xrpl.memo import build_memo, MEMO_NFT_EXPORT
    memos = [build_memo(MEMO_NFT_EXPORT, {"nftId": nftoken_id})]
    d = threads.deferToThread(_create_accept_payload, offer_id, memos)
    d.addCallback(
        lambda payload: _on_accept_payload(
            account, bank, nft_item, nftoken_id, offer_id, payload,
        )
    )
    d.addErrback(
        lambda f: _msg(
            account,
            f"|rError contacting Xaman: {f.getErrorMessage()}|n"
            f"\n|yThe sell offer was created but you couldn't accept it.|n"
            f"\n|yOffer ID: {offer_id}|n",
        )
    )


def _create_accept_payload(offer_id, memos=None):
    """Worker thread — create Xaman accept payload."""
    from blockchain.xrpl.xaman import create_nft_accept_payload
    return create_nft_accept_payload(offer_id, memos=memos)


def _on_accept_payload(account, bank, nft_item, nftoken_id, offer_id,
                       payload):
    """Reactor thread — show deeplink and start polling."""
    if not _connected(account):
        return

    uuid = payload["uuid"]
    deeplink = payload["deeplink"]

    account.msg("|c--- Accept NFT Transfer ---|n")
    account.msg(f"\nOpen this link to sign in Xaman:")
    account.msg(f"|w{deeplink}|n")
    account.msg(f"\nWaiting for you to sign... (2 minute timeout)")

    _poll_xaman_nft_export(account, bank, nft_item, nftoken_id, uuid, attempt=0)


def _on_nft_offer_error(account, failure):
    """Reactor thread — sell offer creation failed."""
    if not _connected(account):
        return
    account.msg(f"|rFailed to create sell offer: {failure.getErrorMessage()}|n")
    account.msg("|yYour item is safe — nothing was moved.|n")


# ================================================================== #
#  Trust line handling
# ================================================================== #

def _handle_missing_trust_line(account, wallet, currency_code):
    """Start trust line setup via Xaman (non-blocking)."""
    from blockchain.xrpl.xrpl_tx import encode_currency_hex
    from blockchain.xrpl.memo import build_memo, MEMO_TRUST

    hex_code = encode_currency_hex(currency_code)
    memos = [build_memo(MEMO_TRUST, {"currency": currency_code})]

    d = threads.deferToThread(_create_trustline_payload, hex_code, memos)
    d.addCallback(
        lambda payload: _on_trustline_payload(
            account, currency_code, payload,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError contacting Xaman: {f.getErrorMessage()}|n")
    )


def _create_trustline_payload(hex_code, memos=None):
    """Worker thread — create Xaman trust line payload."""
    from blockchain.xrpl.xaman import create_trustline_payload
    return create_trustline_payload(hex_code, settings.XRPL_ISSUER_ADDRESS,
                                    memos=memos)


def _on_trustline_payload(account, currency_code, payload):
    """Reactor thread — show deeplink and start polling."""
    if not _connected(account):
        return

    uuid = payload["uuid"]
    deeplink = payload["deeplink"]

    account.msg(
        f"|y--- Trust Line Required ---|n"
        f"\nYour wallet needs a trust line for |w{currency_code}|n"
        f" before you can receive it."
        f"\n\nOpen this link to set it up in Xaman:"
    )
    account.msg(f"|w{deeplink}|n")
    account.msg(f"\nWaiting for you to sign... (2 minute timeout)")

    _poll_xaman_trust_line(account, uuid, currency_code, attempt=0)


# ================================================================== #
#  Polling (non-blocking via deferToThread + delay)
# ================================================================== #

def _poll_xaman_trust_line(account, uuid, currency_code, attempt):
    """Poll Xaman for trust line signing result (non-blocking)."""
    if attempt >= MAX_POLL_ATTEMPTS:
        _msg(account, "|r--- Timed out waiting for Xaman signing ---|n")
        return

    d = threads.deferToThread(_get_payload_status, uuid)
    d.addCallback(
        lambda status: _on_trust_poll_result(
            account, uuid, currency_code, attempt, status,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError polling Xaman: {f.getErrorMessage()}|n")
    )


def _on_trust_poll_result(account, uuid, currency_code, attempt, status):
    """Reactor thread — process trust line poll result."""
    if status["expired"]:
        _msg(account, "|r--- Xaman request expired ---|n")
        return

    if not status["resolved"]:
        delay(2, _poll_xaman_trust_line, account, uuid, currency_code,
              attempt + 1)
        return

    if not status["signed"]:
        _msg(account, "|r--- Trust line request was rejected ---|n")
        return

    _msg(
        account,
        f"|g--- Trust Line Set ---|n"
        f"\nTrust line for |w{currency_code}|n is now active."
        f"\nRun your |wexport|n command again to complete the transfer.",
    )


def _poll_xaman_nft_export(account, bank, nft_item, nftoken_id, uuid,
                           attempt):
    """Poll Xaman for NFT accept offer result (non-blocking)."""
    if attempt >= MAX_POLL_ATTEMPTS:
        _msg(account, "|r--- Timed out waiting for Xaman signing ---|n")
        _msg(account, "|yThe sell offer may still be pending. Try again later.|n")
        return

    d = threads.deferToThread(_get_payload_status, uuid)
    d.addCallback(
        lambda status: _on_nft_poll_result(
            account, bank, nft_item, nftoken_id, uuid, attempt, status,
        )
    )
    d.addErrback(
        lambda f: _msg(account, f"|rError polling Xaman: {f.getErrorMessage()}|n")
    )


def _on_nft_poll_result(account, bank, nft_item, nftoken_id, uuid, attempt,
                        status):
    """Reactor thread — process NFT export poll result."""
    if status["expired"]:
        _msg(account, "|r--- Xaman request expired ---|n")
        return

    if not status["resolved"]:
        delay(2, _poll_xaman_nft_export, account, bank, nft_item,
              nftoken_id, uuid, attempt + 1)
        return

    if not status["signed"]:
        _msg(account, "|r--- NFT transfer was rejected ---|n")
        return

    tx_hash = status.get("tx_hash")

    from blockchain.xrpl.services.nft import NFTService

    try:
        NFTService.withdraw_to_chain(nftoken_id, tx_hash)
    except ValueError as e:
        _msg(account, f"|rDB error after NFT transfer: {e}|n")
        _msg(account, f"|yTx hash: {tx_hash} — contact an admin.|n")
        return

    name = nft_item.key
    try:
        nft_item.delete()
    except Exception:
        pass  # DB state already updated, object cleanup is best-effort

    _msg(
        account,
        f"|g--- Export Complete ---|n"
        f"\n|w{name}|n has been sent to your wallet."
        f"\nTx: |w{tx_hash}|n",
    )


# ================================================================== #
#  Worker thread helpers (no Evennia object access)
# ================================================================== #

def _check_trust_line(wallet, currency_code):
    """Worker thread — check trust line on XRPL."""
    from blockchain.xrpl.xrpl_tx import check_trust_line
    return check_trust_line(wallet, currency_code)


def _send_payment(wallet, currency_code, amount, memos=None):
    """Worker thread — vault sends payment to player wallet."""
    from blockchain.xrpl.xrpl_tx import send_payment
    return send_payment(wallet, currency_code, amount, memos=memos)


def _get_payload_status(uuid):
    """Worker thread — poll Xaman API."""
    from blockchain.xrpl.xaman import get_payload_status
    return get_payload_status(uuid)


# ================================================================== #
#  Shared helpers
# ================================================================== #

def _on_export_payment_error(account, failure, asset_name):
    """Reactor thread — handle payment failure."""
    if not _connected(account):
        return
    from blockchain.xrpl.xrpl_tx import XRPLTransactionError
    error = failure.value
    if isinstance(error, XRPLTransactionError):
        account.msg(f"|rExport failed: {error}|n")
    else:
        account.msg(f"|rUnexpected error: {failure.getErrorMessage()}|n")
    account.msg(f"|yYour {asset_name} is safe — nothing was moved.|n")


def _connected(account):
    """True if the account still has an active session."""
    return account.sessions.count() > 0


def _msg(account, text):
    """Send a message only if the account is still connected."""
    if _connected(account):
        account.msg(text)
