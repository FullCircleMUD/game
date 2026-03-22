"""
XRPL transaction utilities for import/export operations.

Server-side XRPL operations using xrpl-py. The vault wallet signs
transactions directly (using seed from settings). Player-signed
transactions go through Xaman (see xaman.py).

Uses the same async websocket pattern as chain_sync.py.
"""

import asyncio
import logging

from django.conf import settings

from decimal import Decimal

from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import AccountLines, AccountNFTs, Tx
from xrpl.models.transactions import (
    NFTokenAcceptOffer, NFTokenCreateOffer, Payment,
)
from xrpl.wallet import Wallet

logger = logging.getLogger("evennia")


# ================================================================== #
#  Currency code encoding
# ================================================================== #

def encode_currency_hex(code):
    """
    Encode a currency code for XRPL transactions.

    Standard 3-char codes (e.g., "USD") pass through unchanged.
    Longer codes (e.g., "FCMGold") are hex-encoded and zero-padded
    to 40 characters (20 bytes / 160 bits) per XRPL spec.
    """
    if len(code) <= 3:
        return code
    return code.encode("ascii").hex().upper().ljust(40, "0")


def decode_currency_hex(hex_code):
    """
    Decode an XRPL hex currency code back to a readable string.

    3-char codes pass through unchanged. 40-char hex codes are
    decoded and null-bytes stripped.
    """
    if len(hex_code) <= 3:
        return hex_code
    try:
        return bytes.fromhex(hex_code).rstrip(b"\x00").decode("ascii")
    except (ValueError, UnicodeDecodeError):
        return hex_code


# ================================================================== #
#  Trust line queries
# ================================================================== #

async def _check_trust_line_async(network_url, wallet_address,
                                  currency_code, issuer_address):
    """Check if a wallet has a trust line for the given currency."""
    async with AsyncWebsocketClient(network_url) as client:
        response = await client.request(
            AccountLines(
                account=wallet_address,
                peer=issuer_address,
                ledger_index="validated",
            )
        )
        lines = response.result.get("lines", [])
        target_hex = encode_currency_hex(currency_code)
        for line in lines:
            if line["currency"] == target_hex:
                return True
        return False


def check_trust_line(wallet_address, currency_code):
    """
    Check if a player's wallet has a trust line for the given currency.

    Args:
        wallet_address: Player's r-address.
        currency_code: Game currency code (e.g., "FCMGold").

    Returns:
        True if trust line exists, False otherwise.
    """
    return asyncio.run(
        _check_trust_line_async(
            settings.XRPL_NETWORK_URL,
            wallet_address,
            currency_code,
            settings.XRPL_ISSUER_ADDRESS,
        )
    )


# ================================================================== #
#  Fungible payment (vault → player)
# ================================================================== #

async def _send_payment_async(network_url, vault_seed, destination,
                              currency_code, amount, issuer_address):
    """Build, sign, and submit a Payment from vault to player."""
    wallet = Wallet.from_seed(vault_seed)

    tx = Payment(
        account=wallet.address,
        destination=destination,
        amount=IssuedCurrencyAmount(
            currency=encode_currency_hex(currency_code),
            value=str(amount),
            issuer=issuer_address,
        ),
    )

    async with AsyncWebsocketClient(network_url) as client:
        result = await submit_and_wait(tx, client, wallet)

    tx_result = result.result.get("meta", {}).get("TransactionResult")
    tx_hash = result.result.get("hash")

    if tx_result != "tesSUCCESS":
        raise XRPLTransactionError(
            f"Payment failed: {tx_result}", tx_hash=tx_hash,
            result_code=tx_result,
        )

    logger.log_info(
        f"XRPL Payment: {amount} {currency_code} → {destination} "
        f"(tx: {tx_hash})"
    )
    return tx_hash


def send_payment(destination, currency_code, amount):
    """
    Send an issued currency payment from the vault to a player wallet.

    Args:
        destination: Player's r-address.
        currency_code: Game currency code (e.g., "FCMGold").
        amount: Amount to send (int or Decimal — converted to string).

    Returns:
        tx_hash (str): The XRPL transaction hash.

    Raises:
        XRPLTransactionError: If the transaction fails.
    """
    return asyncio.run(
        _send_payment_async(
            settings.XRPL_NETWORK_URL,
            settings.XRPL_VAULT_WALLET_SEED,
            destination,
            currency_code,
            amount,
            settings.XRPL_ISSUER_ADDRESS,
        )
    )


# ================================================================== #
#  NFT sell offer (vault creates offer for player to accept)
# ================================================================== #

async def _create_nft_sell_offer_async(network_url, vault_seed,
                                       nftoken_id, destination):
    """Create a sell offer for 0 XRP, destined for a specific player."""
    wallet = Wallet.from_seed(vault_seed)

    tx = NFTokenCreateOffer(
        account=wallet.address,
        nftoken_id=nftoken_id,
        amount="0",  # Free transfer
        destination=destination,
        flags=0x00000001,  # tfSellNFToken
    )

    async with AsyncWebsocketClient(network_url) as client:
        result = await submit_and_wait(tx, client, wallet)

    tx_result = result.result.get("meta", {}).get("TransactionResult")
    tx_hash = result.result.get("hash")

    if tx_result != "tesSUCCESS":
        raise XRPLTransactionError(
            f"NFTokenCreateOffer failed: {tx_result}", tx_hash=tx_hash,
            result_code=tx_result,
        )

    # Extract the offer ID from affected nodes
    offer_id = _extract_offer_id(result.result.get("meta", {}))
    if not offer_id:
        raise XRPLTransactionError(
            "Could not extract offer ID from transaction metadata",
            tx_hash=tx_hash,
        )

    logger.log_info(
        f"XRPL NFT Sell Offer: {nftoken_id} → {destination} "
        f"(offer: {offer_id}, tx: {tx_hash})"
    )
    return tx_hash, offer_id


def _extract_offer_id(meta):
    """
    Extract the NFTokenOffer ID from transaction metadata.

    The offer node is a CreatedNode of type NFTokenOffer in AffectedNodes.
    """
    for node in meta.get("AffectedNodes", []):
        created = node.get("CreatedNode", {})
        if created.get("LedgerEntryType") == "NFTokenOffer":
            return created.get("LedgerIndex")
    return None


def create_nft_sell_offer(nftoken_id, destination):
    """
    Create an NFT sell offer from the vault to a player.

    The vault creates a sell offer for 0 XRP, targeted at the player.
    The player must then accept this offer via Xaman.

    Args:
        nftoken_id: The 64-char NFToken ID on-chain.
        destination: Player's r-address.

    Returns:
        (tx_hash, offer_id) tuple.

    Raises:
        XRPLTransactionError: If the transaction fails.
    """
    return asyncio.run(
        _create_nft_sell_offer_async(
            settings.XRPL_NETWORK_URL,
            settings.XRPL_VAULT_WALLET_SEED,
            nftoken_id,
            destination,
        )
    )


# ================================================================== #
#  NFT accept offer (vault accepts player's sell offer for import)
# ================================================================== #

async def _accept_nft_sell_offer_async(network_url, vault_seed, offer_id):
    """Accept a player's NFT sell offer (vault-signed)."""
    wallet = Wallet.from_seed(vault_seed)

    tx = NFTokenAcceptOffer(
        account=wallet.address,
        nftoken_sell_offer=offer_id,
    )

    async with AsyncWebsocketClient(network_url) as client:
        result = await submit_and_wait(tx, client, wallet)

    tx_result = result.result.get("meta", {}).get("TransactionResult")
    tx_hash = result.result.get("hash")

    if tx_result != "tesSUCCESS":
        raise XRPLTransactionError(
            f"NFTokenAcceptOffer failed: {tx_result}", tx_hash=tx_hash,
            result_code=tx_result,
        )

    logger.log_info(
        f"XRPL NFT Accept Offer: {offer_id} (tx: {tx_hash})"
    )
    return tx_hash


def accept_nft_sell_offer(offer_id):
    """
    Accept a player's NFT sell offer from the vault.

    The vault accepts the player's sell offer, completing the NFT import.

    Args:
        offer_id: The NFTokenOffer ledger index (64-char hex).

    Returns:
        tx_hash (str): The XRPL transaction hash.

    Raises:
        XRPLTransactionError: If the transaction fails.
    """
    return asyncio.run(
        _accept_nft_sell_offer_async(
            settings.XRPL_NETWORK_URL,
            settings.XRPL_VAULT_WALLET_SEED,
            offer_id,
        )
    )


# ================================================================== #
#  Transaction query (for extracting offer IDs from signed txns)
# ================================================================== #

async def _get_transaction_async(network_url, tx_hash):
    """Query a transaction's full result from the XRPL ledger."""
    async with AsyncWebsocketClient(network_url) as client:
        response = await client.request(
            Tx(transaction=tx_hash)
        )
        return response.result


def get_transaction(tx_hash):
    """
    Query a confirmed transaction's result from the XRPL ledger.

    Used to extract offer IDs from NFTokenCreateOffer transactions
    signed by players via Xaman.

    Args:
        tx_hash: The transaction hash to look up.

    Returns:
        dict: The full transaction result including metadata.
    """
    return asyncio.run(
        _get_transaction_async(
            settings.XRPL_NETWORK_URL,
            tx_hash,
        )
    )


def verify_fungible_payment(tx_hash, expected_destination, expected_currency_hex,
                            expected_amount, expected_issuer):
    """
    Verify a Payment transaction on-chain matches expected parameters.

    Queries the XRPL ledger for the transaction and checks that it is
    a successful Payment to the expected destination with the correct
    currency, issuer, and amount.

    Args:
        tx_hash: The transaction hash to verify.
        expected_destination: Expected Payment destination (vault address).
        expected_currency_hex: Expected hex-encoded currency code.
        expected_amount: Expected amount (int or Decimal).
        expected_issuer: Expected currency issuer address.

    Returns:
        Decimal: The verified amount from the on-chain transaction.

    Raises:
        XRPLTransactionError: If verification fails for any reason.
    """
    try:
        tx_result = get_transaction(tx_hash)
    except Exception as e:
        raise XRPLTransactionError(
            f"Could not query transaction {tx_hash}: {e}",
            tx_hash=tx_hash,
        )

    # Check transaction succeeded
    meta_result = tx_result.get("meta", {}).get("TransactionResult")
    if meta_result != "tesSUCCESS":
        raise XRPLTransactionError(
            f"Transaction was not successful: {meta_result}",
            tx_hash=tx_hash, result_code=meta_result,
        )

    # Check it's a Payment
    if tx_result.get("TransactionType") != "Payment":
        raise XRPLTransactionError(
            f"Transaction is not a Payment "
            f"(got {tx_result.get('TransactionType')})",
            tx_hash=tx_hash,
        )

    # Check destination
    if tx_result.get("Destination") != expected_destination:
        raise XRPLTransactionError(
            f"Payment destination mismatch: "
            f"expected {expected_destination}, "
            f"got {tx_result.get('Destination')}",
            tx_hash=tx_hash,
        )

    # Check amount is an issued currency (dict), not XRP (string)
    amount = tx_result.get("Amount")
    if not isinstance(amount, dict):
        raise XRPLTransactionError(
            "Payment amount is XRP, not an issued currency",
            tx_hash=tx_hash,
        )

    # Check currency code
    if amount.get("currency") != expected_currency_hex:
        raise XRPLTransactionError(
            f"Currency mismatch: expected {expected_currency_hex}, "
            f"got {amount.get('currency')}",
            tx_hash=tx_hash,
        )

    # Check issuer
    if amount.get("issuer") != expected_issuer:
        raise XRPLTransactionError(
            f"Issuer mismatch: expected {expected_issuer}, "
            f"got {amount.get('issuer')}",
            tx_hash=tx_hash,
        )

    # Check amount
    on_chain_amount = Decimal(amount.get("value", "0"))
    if on_chain_amount < Decimal(str(expected_amount)):
        raise XRPLTransactionError(
            f"Amount mismatch: expected {expected_amount}, "
            f"got {on_chain_amount}",
            tx_hash=tx_hash,
        )

    return on_chain_amount


# ================================================================== #
#  Wallet queries (read-only, for wallet display)
# ================================================================== #

async def _get_wallet_balances_async(network_url, wallet_address,
                                     issuer_address):
    """Query all game currency balances held by a player wallet."""
    async with AsyncWebsocketClient(network_url) as client:
        response = await client.request(
            AccountLines(
                account=wallet_address,
                peer=issuer_address,
                ledger_index="validated",
            )
        )
        balances = {}
        for line in response.result.get("lines", []):
            balance = Decimal(line["balance"])
            if balance > 0:
                currency_code = decode_currency_hex(line["currency"])
                balances[currency_code] = balance
        return balances


def get_wallet_balances(wallet_address):
    """
    Query all game currency balances for a player wallet.

    Returns dict of {currency_code: Decimal balance} for currencies
    with balance > 0. Currency codes are decoded (e.g., "FCMGold").
    """
    return asyncio.run(
        _get_wallet_balances_async(
            settings.XRPL_NETWORK_URL,
            wallet_address,
            settings.XRPL_ISSUER_ADDRESS,
        )
    )


async def _get_wallet_nfts_async(network_url, wallet_address):
    """Query all NFTs owned by a player wallet."""
    all_nfts = []
    marker = None
    async with AsyncWebsocketClient(network_url) as client:
        while True:
            kwargs = {"account": wallet_address, "limit": 100}
            if marker:
                kwargs["marker"] = marker
            response = await client.request(AccountNFTs(**kwargs))
            nfts = response.result.get("account_nfts", [])
            all_nfts.extend(nfts)
            marker = response.result.get("marker")
            if not marker:
                break
    return all_nfts


def get_wallet_nfts(wallet_address):
    """
    Query game NFTs owned by a player wallet.

    Returns list of dicts with nftoken_id and name. Cross-references
    NFTGameState for item names. Unknown NFTs shown as "Unknown NFT".
    """
    from blockchain.xrpl.models import NFTGameState

    raw_nfts = asyncio.run(
        _get_wallet_nfts_async(
            settings.XRPL_NETWORK_URL,
            wallet_address,
        )
    )

    results = []
    for nft in raw_nfts:
        nftoken_id = nft["NFTokenID"]
        name = "Unknown NFT"
        try:
            game_nft = NFTGameState.objects.select_related("item_type").get(
                nftoken_id=nftoken_id,
            )
            if game_nft.item_type:
                name = game_nft.item_type.name
        except NFTGameState.DoesNotExist:
            pass
        results.append({"nftoken_id": nftoken_id, "name": name})

    return results


# ================================================================== #
#  Exceptions
# ================================================================== #

class XRPLTransactionError(Exception):
    """Raised when an XRPL transaction fails."""

    def __init__(self, message, tx_hash=None, result_code=None):
        super().__init__(message)
        self.tx_hash = tx_hash
        self.result_code = result_code
