"""
XRPL AMM utilities for pool queries and swap execution.

Low-level XRPL AMM operations: query pool reserves, calculate swap
quotes using the constant product formula, and execute swaps via
vault-to-vault cross-currency Payments routed through AMM pools.

Same async/sync wrapper pattern as xrpl_tx.py.
"""

import asyncio
import logging
import math

from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR

from django.conf import settings

from xrpl.asyncio.clients import AsyncWebsocketClient
from xrpl.asyncio.transaction import submit_and_wait
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.currencies import IssuedCurrency
from xrpl.models.requests import AMMInfo
from xrpl.models.transactions import OfferCreate, OfferCreateFlag
from xrpl.wallet import Wallet

from blockchain.xrpl.xrpl_tx import (
    XRPLTransactionError,
    encode_currency_hex,
    decode_currency_hex,
)

logger = logging.getLogger("evennia")


# ================================================================== #
#  Pool queries
# ================================================================== #

async def _get_amm_info_async(network_url, currency_code_1, currency_code_2,
                               issuer_address):
    """Query AMM pool info for a currency pair."""
    asset1 = IssuedCurrency(
        currency=encode_currency_hex(currency_code_1),
        issuer=issuer_address,
    )
    asset2 = IssuedCurrency(
        currency=encode_currency_hex(currency_code_2),
        issuer=issuer_address,
    )

    async with AsyncWebsocketClient(network_url) as client:
        response = await client.request(
            AMMInfo(asset=asset1, asset2=asset2)
        )

    result = response.result
    if "amm" not in result:
        return None

    amm = result["amm"]

    # Parse reserves — issued currency amounts are dicts
    amount1 = amm["amount"]
    amount2 = amm["amount2"]

    def _parse_amount(amt):
        """Parse an AMM amount (either XRP drops string or issued currency dict)."""
        if isinstance(amt, str):
            # XRP in drops — not expected for our pools but handle it
            return {"currency": "XRP", "value": Decimal(amt) / 1000000}
        return {
            "currency": decode_currency_hex(amt["currency"]),
            "value": Decimal(amt["value"]),
        }

    r1 = _parse_amount(amount1)
    r2 = _parse_amount(amount2)

    return {
        "reserve_1": r1,
        "reserve_2": r2,
        "trading_fee": amm.get("trading_fee", 0),
        "lp_token": amm.get("lp_token"),
        "amm_account": amm.get("account"),
    }


def get_amm_info(currency_code_1, currency_code_2):
    """
    Query AMM pool info for a pair of game currencies.

    Args:
        currency_code_1: First currency (e.g., "FCMGold").
        currency_code_2: Second currency (e.g., "FCMWheat").

    Returns:
        dict with reserve_1, reserve_2, trading_fee, lp_token, amm_account.
        None if no pool exists.
    """
    return asyncio.run(
        _get_amm_info_async(
            settings.XRPL_NETWORK_URL,
            currency_code_1,
            currency_code_2,
            settings.XRPL_ISSUER_ADDRESS,
        )
    )


# ================================================================== #
#  Constant product price calculation
# ================================================================== #

def calculate_buy_cost(reserve_in, reserve_out, amount_out, trading_fee):
    """
    Calculate how much input is needed to buy `amount_out` of the output token.

    Uses the constant product formula with fee:
        fee_factor = 1 - (trading_fee / 100000)
        input_needed = (reserve_in * amount_out) / ((reserve_out - amount_out) * fee_factor)

    Args:
        reserve_in: Decimal — pool reserve of input currency (e.g., FCMGold).
        reserve_out: Decimal — pool reserve of output currency (e.g., FCMWheat).
        amount_out: int — desired amount of output currency.
        trading_fee: int — XRPL AMM fee in units of 1/100000 (e.g., 100 = 0.1%).

    Returns:
        Decimal — exact input amount needed (before rounding).

    Raises:
        ValueError if amount_out >= reserve_out (pool can't fill the order).
    """
    amount_out = Decimal(str(amount_out))
    if amount_out >= reserve_out:
        raise ValueError(
            f"Cannot buy {amount_out} — pool only has {reserve_out}"
        )
    fee_factor = Decimal(1) - Decimal(trading_fee) / Decimal(100000)
    return (reserve_in * amount_out) / ((reserve_out - amount_out) * fee_factor)


def calculate_sell_output(reserve_in, reserve_out, amount_in, trading_fee):
    """
    Calculate how much output is received from selling `amount_in` of the input token.

    Uses the constant product formula with fee:
        fee_factor = 1 - (trading_fee / 100000)
        input_after_fee = amount_in * fee_factor
        output = (reserve_out * input_after_fee) / (reserve_in + input_after_fee)

    Args:
        reserve_in: Decimal — pool reserve of input currency (e.g., FCMWheat).
        reserve_out: Decimal — pool reserve of output currency (e.g., FCMGold).
        amount_in: int — amount of input currency to sell.
        trading_fee: int — XRPL AMM fee in units of 1/100000.

    Returns:
        Decimal — exact output amount received (before rounding).
    """
    amount_in = Decimal(str(amount_in))
    fee_factor = Decimal(1) - Decimal(trading_fee) / Decimal(100000)
    input_after_fee = amount_in * fee_factor
    return (reserve_out * input_after_fee) / (reserve_in + input_after_fee)


def get_swap_quote(resource_currency, amount, direction="buy",
                   gold_currency=None):
    """
    Get a swap quote for buying or selling a resource against a gold currency.

    Args:
        resource_currency: Currency code of the resource (e.g., "FCMWheat").
        amount: int — amount of resource to buy or sell.
        direction: "buy" (gold → resource) or "sell" (resource → gold).
        gold_currency: Optional gold currency code. Defaults to FCMGold.
            Pass settings.XRPL_PGOLD_CURRENCY_CODE for NFT proxy token pools.

    Returns:
        dict with:
            input_amount: Decimal — exact input needed.
            output_amount: Decimal — exact output received.
            gold_cost_rounded: int — ceil-rounded gold cost (for buys).
            gold_received_rounded: int — floor-rounded gold received (for sells).
            price_per_unit: Decimal — gold per 1 unit of resource.

    Raises:
        ValueError if pool doesn't exist or can't fill the order.
    """
    if gold_currency is None:
        gold_currency = settings.XRPL_GOLD_CURRENCY_CODE

    info = get_amm_info(gold_currency, resource_currency)
    if info is None:
        raise ValueError(
            f"No AMM pool found for {gold_currency}/{resource_currency}"
        )

    # Identify which reserve is gold and which is the resource
    r1 = info["reserve_1"]
    r2 = info["reserve_2"]

    if r1["currency"] == gold_currency:
        gold_reserve = r1["value"]
        resource_reserve = r2["value"]
    elif r2["currency"] == gold_currency:
        gold_reserve = r2["value"]
        resource_reserve = r1["value"]
    else:
        raise ValueError(
            f"Pool does not contain {gold_currency}: "
            f"found {r1['currency']}/{r2['currency']}"
        )

    fee = info["trading_fee"]

    if direction == "buy":
        # Buying resource with gold
        exact_gold = calculate_buy_cost(
            gold_reserve, resource_reserve, amount, fee,
        )
        gold_rounded = int(math.ceil(float(exact_gold)))
        return {
            "input_amount": exact_gold,
            "output_amount": Decimal(str(amount)),
            "gold_cost_rounded": gold_rounded,
            "gold_received_rounded": None,
            "price_per_unit": exact_gold / Decimal(str(amount)),
        }

    elif direction == "sell":
        # Selling resource for gold
        exact_gold = calculate_sell_output(
            resource_reserve, gold_reserve, amount, fee,
        )
        gold_rounded = int(math.floor(float(exact_gold)))
        return {
            "input_amount": Decimal(str(amount)),
            "output_amount": exact_gold,
            "gold_cost_rounded": None,
            "gold_received_rounded": gold_rounded,
            "price_per_unit": exact_gold / Decimal(str(amount)),
        }

    else:
        raise ValueError(f"Invalid direction: {direction}")


async def _get_multi_pool_prices_async(network_url, gold_currency,
                                        resource_currencies, issuer_address):
    """Query multiple AMM pools in a single websocket session."""
    gold_hex = encode_currency_hex(gold_currency)
    gold_asset = IssuedCurrency(currency=gold_hex, issuer=issuer_address)

    results = {}

    async with AsyncWebsocketClient(network_url) as client:
        for rc in resource_currencies:
            resource_hex = encode_currency_hex(rc)
            resource_asset = IssuedCurrency(
                currency=resource_hex, issuer=issuer_address,
            )
            try:
                response = await client.request(
                    AMMInfo(asset=gold_asset, asset2=resource_asset)
                )
                amm = response.result.get("amm")
                if not amm:
                    continue

                # Parse reserves
                a1 = amm["amount"]
                a2 = amm["amount2"]

                def _get_value(amt):
                    if isinstance(amt, str):
                        return Decimal(amt) / 1000000
                    return Decimal(amt["value"])

                def _get_currency(amt):
                    if isinstance(amt, str):
                        return "XRP"
                    return decode_currency_hex(amt["currency"])

                c1, v1 = _get_currency(a1), _get_value(a1)
                c2, v2 = _get_currency(a2), _get_value(a2)

                if c1 == gold_currency:
                    gold_reserve, resource_reserve = v1, v2
                elif c2 == gold_currency:
                    gold_reserve, resource_reserve = v2, v1
                else:
                    continue

                fee = amm.get("trading_fee", 0)

                # Price for 1 unit
                buy_1 = calculate_buy_cost(
                    gold_reserve, resource_reserve, 1, fee,
                )
                sell_1 = calculate_sell_output(
                    resource_reserve, gold_reserve, 1, fee,
                )

                results[rc] = {
                    "buy_1": int(math.ceil(float(buy_1))),
                    "sell_1": int(math.floor(float(sell_1))),
                    "gold_reserve": gold_reserve,
                    "resource_reserve": resource_reserve,
                }

            except Exception as e:
                logger.warning(
                    f"AMM pool query failed for {gold_currency}/{rc}: {e}"
                )
                continue

    return results


def get_multi_pool_prices(resource_currencies, gold_currency=None):
    """
    Query prices for multiple resource/gold AMM pools.

    Args:
        resource_currencies: list of currency codes (e.g., ["FCMWheat", "FCMFlour"]).
        gold_currency: Optional gold currency code. Defaults to FCMGold.
            Pass settings.XRPL_PGOLD_CURRENCY_CODE for NFT proxy token pools.

    Returns:
        dict {currency_code: {buy_1: int, sell_1: int, gold_reserve, resource_reserve}}.
        Missing pools are omitted.
    """
    if gold_currency is None:
        gold_currency = settings.XRPL_GOLD_CURRENCY_CODE
    return asyncio.run(
        _get_multi_pool_prices_async(
            settings.XRPL_NETWORK_URL,
            gold_currency,
            resource_currencies,
            settings.XRPL_ISSUER_ADDRESS,
        )
    )


# ================================================================== #
#  Swap execution
# ================================================================== #

async def _execute_swap_async(network_url, vault_seed, issuer_address,
                               from_currency, to_currency,
                               max_input, expected_output):
    """
    Execute a cross-currency swap via OfferCreate on the XRPL DEX.

    Uses a fill-or-kill offer that the AMM pool fills immediately.
    This avoids the self-payment limitation (XRPL won't route
    cross-currency Payments where account == destination).

    taker_gets = what we're selling (from_currency, max_input)
    taker_pays = what we're buying  (to_currency, expected_output)
    """
    wallet = Wallet.from_seed(vault_seed)

    tx = OfferCreate(
        account=wallet.address,
        taker_gets=IssuedCurrencyAmount(
            currency=encode_currency_hex(from_currency),
            value=str(max_input),
            issuer=issuer_address,
        ),
        taker_pays=IssuedCurrencyAmount(
            currency=encode_currency_hex(to_currency),
            value=str(expected_output),
            issuer=issuer_address,
        ),
        flags=OfferCreateFlag.TF_IMMEDIATE_OR_CANCEL,
    )

    async with AsyncWebsocketClient(network_url) as client:
        result = await submit_and_wait(tx, client, wallet)

    tx_result = result.result.get("meta", {}).get("TransactionResult")
    tx_hash = result.result.get("hash")

    if tx_result != "tesSUCCESS":
        raise XRPLTransactionError(
            f"AMM swap failed: {tx_result}",
            tx_hash=tx_hash,
            result_code=tx_result,
        )

    # Extract actual amounts from balance changes in metadata
    meta = result.result.get("meta", {})
    actual_input = _extract_balance_change(
        meta, wallet.address, from_currency, issuer_address,
    )
    actual_output = _extract_balance_change(
        meta, wallet.address, to_currency, issuer_address,
    )
    if actual_input is None:
        actual_input = Decimal(str(max_input))
    if actual_output is None:
        actual_output = Decimal(str(expected_output))

    logger.info(
        f"XRPL AMM Swap: {actual_input} {from_currency} → "
        f"{actual_output} {to_currency} (tx: {tx_hash})"
    )

    return {
        "tx_hash": tx_hash,
        "actual_input": actual_input,
        "actual_output": actual_output,
    }


def _extract_balance_change(meta, account, currency, issuer_address):
    """
    Extract the absolute balance change for a currency from OfferCreate metadata.

    Scans AffectedNodes for the RippleState (trust line) entry matching
    the given currency and account, then returns abs(final - previous).

    Returns Decimal or None if the trust line wasn't found in metadata.
    """
    currency_hex = encode_currency_hex(currency)
    for node in meta.get("AffectedNodes", []):
        modified = node.get("ModifiedNode", {})
        if modified.get("LedgerEntryType") != "RippleState":
            continue
        fields = modified.get("FinalFields", {})
        prev = modified.get("PreviousFields", {})
        balance = fields.get("Balance", {})
        prev_balance = prev.get("Balance", {})
        if balance.get("currency") != currency_hex:
            continue
        low = fields.get("LowLimit", {})
        high = fields.get("HighLimit", {})
        if account not in (low.get("issuer"), high.get("issuer")):
            continue
        if "value" in prev_balance and "value" in balance:
            diff = Decimal(balance["value"]) - Decimal(prev_balance["value"])
            return abs(diff)
    return None


def execute_swap(from_currency, to_currency, max_input, expected_output):
    """
    Execute a cross-currency swap through the AMM pool.

    Uses a fill-or-kill OfferCreate on the XRPL DEX.
    taker_gets = max_input of from_currency (what vault sells).
    taker_pays = expected_output of to_currency (what vault receives).

    Args:
        from_currency: Currency code to spend (e.g., "FCMGold").
        to_currency: Currency code to receive (e.g., "FCMWheat").
        max_input: Maximum input amount (rounded integer).
        expected_output: Expected output amount.

    Returns:
        dict with tx_hash, actual_output.

    Raises:
        XRPLTransactionError if the swap fails (e.g., price moved beyond max_input).
    """
    return asyncio.run(
        _execute_swap_async(
            settings.XRPL_NETWORK_URL,
            settings.XRPL_VAULT_WALLET_SEED,
            settings.XRPL_ISSUER_ADDRESS,
            from_currency,
            to_currency,
            max_input,
            expected_output,
        )
    )
