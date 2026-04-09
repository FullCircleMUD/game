"""
Xaman (XRPL wallet) API wrapper.

Creates payloads for Xaman wallet signing:
  - SignIn (proof of wallet ownership for login)
  - TrustSet (player sets up a trust line for a currency)
  - NFTokenAcceptOffer (player accepts an NFT sell offer)

Uses raw `requests` library — no xumm-sdk-py dependency needed.

Credentials (XAMAN_API_KEY, XAMAN_API_SECRET) must be set in
secret_settings.py. Register at https://apps.xaman.dev/ to obtain them.
"""

import requests
from django.conf import settings

from blockchain.xrpl.memo import memo_to_xaman

XAMAN_BASE_URL = "https://xumm.app/api/v1/platform"


class XamanAPIError(Exception):
    """Raised when a Xaman API call fails."""
    pass


def _headers():
    """Return auth headers for Xaman API calls."""
    return {
        "Content-Type": "application/json",
        "X-API-Key": settings.XAMAN_API_KEY,
        "X-API-Secret": settings.XAMAN_API_SECRET,
    }


def create_signin_payload():
    """
    Create a Xaman SignIn payload.

    Returns:
        dict with keys:
            uuid (str): Payload UUID for polling
            deeplink (str): URL the user opens to sign
            qr_url (str): URL to QR code image

    Raises:
        XamanAPIError: If the API call fails.
    """
    resp = requests.post(
        f"{XAMAN_BASE_URL}/payload",
        json={"txjson": {"TransactionType": "SignIn"}},
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code != 200:
        raise XamanAPIError(f"Xaman API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return {
        "uuid": data["uuid"],
        "deeplink": data["next"]["always"],
        "qr_url": data["refs"]["qr_png"],
    }


def get_payload_status(uuid):
    """
    Poll a Xaman payload for its current status.

    Args:
        uuid (str): The payload UUID returned by create_signin_payload().

    Returns:
        dict with keys:
            resolved (bool): Whether the user has acted (signed or rejected)
            signed (bool): Whether the user signed
            wallet_address (str or None): The r-address if signed
            expired (bool): Whether the payload expired
    """
    resp = requests.get(
        f"{XAMAN_BASE_URL}/payload/{uuid}",
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code != 200:
        raise XamanAPIError(f"Xaman API error {resp.status_code}: {resp.text}")

    data = resp.json()
    meta = data.get("meta", {})
    response = data.get("response", {})

    return {
        "resolved": meta.get("resolved", False),
        "signed": meta.get("signed", False),
        "wallet_address": response.get("account", None),
        "expired": meta.get("expired", False),
        "tx_hash": response.get("txid", None),
    }


def _create_payload(txjson):
    """
    Create a Xaman payload with an arbitrary transaction JSON.

    Returns:
        dict with keys: uuid, deeplink, qr_url

    Raises:
        XamanAPIError: If the API call fails.
    """
    resp = requests.post(
        f"{XAMAN_BASE_URL}/payload",
        json={"txjson": txjson},
        headers=_headers(),
        timeout=10,
    )
    if resp.status_code != 200:
        raise XamanAPIError(f"Xaman API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return {
        "uuid": data["uuid"],
        "deeplink": data["next"]["always"],
        "qr_url": data["refs"]["qr_png"],
    }


def create_trustline_payload(currency_code, issuer_address,
                             limit="1000000000", memos=None):
    """
    Create a Xaman TrustSet payload for the player to sign.

    The player signs this to set up a trust line for a currency,
    which is required before they can receive that currency.

    Args:
        currency_code: Hex-encoded XRPL currency code (40 chars for >3 char codes).
        issuer_address: The currency issuer's r-address.
        limit: Trust line limit (string). Defaults to 1 billion.
        memos: Optional list of xrpl.models.Memo for audit trail.

    Returns:
        dict with keys: uuid, deeplink, qr_url
    """
    txjson = {
        "TransactionType": "TrustSet",
        "LimitAmount": {
            "currency": currency_code,
            "issuer": issuer_address,
            "value": limit,
        },
    }
    if memos:
        txjson["Memos"] = [memo_to_xaman(m) for m in memos]
    return _create_payload(txjson)


def create_payment_payload(destination, currency_code, amount, issuer_address,
                           memos=None):
    """
    Create a Xaman Payment payload for the player to sign.

    The player signs this to send an issued currency payment from their
    wallet to the vault (fungible import or subscription).

    Args:
        destination: The vault's r-address.
        currency_code: Hex-encoded XRPL currency code (40 chars for >3 char codes).
        amount: Amount to send (int/Decimal — converted to string).
        issuer_address: The currency issuer's r-address.
        memos: Optional list of xrpl.models.Memo for audit trail.

    Returns:
        dict with keys: uuid, deeplink, qr_url
    """
    txjson = {
        "TransactionType": "Payment",
        "Destination": destination,
        "Amount": {
            "currency": currency_code,
            "value": str(amount),
            "issuer": issuer_address,
        },
    }
    if memos:
        txjson["Memos"] = [memo_to_xaman(m) for m in memos]
    return _create_payload(txjson)


def create_nft_sell_offer_payload(nftoken_id, destination, memos=None):
    """
    Create a Xaman NFTokenCreateOffer payload for the player to sign.

    The player signs this to create a sell offer for their NFT at 0 XRP,
    targeted at the vault. The vault then accepts it server-side (NFT import).

    Args:
        nftoken_id: The 64-char NFToken ID on-chain.
        destination: The vault's r-address.
        memos: Optional list of xrpl.models.Memo for audit trail.

    Returns:
        dict with keys: uuid, deeplink, qr_url
    """
    txjson = {
        "TransactionType": "NFTokenCreateOffer",
        "NFTokenID": nftoken_id,
        "Amount": "0",
        "Destination": destination,
        "Flags": 1,  # tfSellNFToken
    }
    if memos:
        txjson["Memos"] = [memo_to_xaman(m) for m in memos]
    return _create_payload(txjson)


def create_nft_accept_payload(sell_offer_id, memos=None):
    """
    Create a Xaman NFTokenAcceptOffer payload for the player to sign.

    The player signs this to accept an NFT sell offer created by the vault,
    completing the NFT export transfer.

    Args:
        sell_offer_id: The NFTokenOffer ledger index (64-char hex).
        memos: Optional list of xrpl.models.Memo for audit trail.

    Returns:
        dict with keys: uuid, deeplink, qr_url
    """
    txjson = {
        "TransactionType": "NFTokenAcceptOffer",
        "NFTokenSellOffer": sell_offer_id,
    }
    if memos:
        txjson["Memos"] = [memo_to_xaman(m) for m in memos]
    return _create_payload(txjson)
