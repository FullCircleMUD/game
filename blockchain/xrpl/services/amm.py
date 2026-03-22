"""
AMMService — game-level AMM buy/sell operations.

Bridges the XRPL AMM pool queries (xrpl_amm.py) with the game's
FungibleService state management. Handles rounding (ceil for buys,
floor for sells), on-chain swap execution, and atomic game state updates.

Game code should NOT import this directly — use FungibleInventoryMixin's
buy_from_pool() / sell_to_pool() / get_pool_price() methods.
"""

import logging
import math

from decimal import Decimal

from django.conf import settings
from django.db import transaction

from blockchain.xrpl.models import (
    FungibleGameState,
    FungibleTransferLog,
    XRPLTransactionLog,
)
from blockchain.xrpl.services.fungible import FungibleService
from blockchain.xrpl.currency_cache import get_currency_code

logger = logging.getLogger("evennia")


class AMMService:
    """Game-level AMM operations for buying and selling resources."""

    # ================================================================== #
    #  Price queries
    # ================================================================== #

    @staticmethod
    def get_buy_price(resource_id, amount):
        """
        Get the gold cost to buy `amount` of a resource from the AMM.

        Returns:
            int — gold cost, ceil-rounded (always rounds in game's favor).

        Raises:
            ValueError if pool doesn't exist or can't fill the order.
        """
        from blockchain.xrpl.xrpl_amm import get_swap_quote

        currency_code = get_currency_code(resource_id)
        if not currency_code:
            raise ValueError(f"Unknown resource_id: {resource_id}")

        quote = get_swap_quote(currency_code, amount, direction="buy")
        return quote["gold_cost_rounded"]

    @staticmethod
    def get_sell_price(resource_id, amount):
        """
        Get the gold received from selling `amount` of a resource to the AMM.

        Returns:
            int — gold received, floor-rounded (always rounds in game's favor).

        Raises:
            ValueError if pool doesn't exist.
        """
        from blockchain.xrpl.xrpl_amm import get_swap_quote

        currency_code = get_currency_code(resource_id)
        if not currency_code:
            raise ValueError(f"Unknown resource_id: {resource_id}")

        quote = get_swap_quote(currency_code, amount, direction="sell")
        return quote["gold_received_rounded"]

    @staticmethod
    def get_pool_prices(resource_ids):
        """
        Get buy/sell prices for multiple resources in a single websocket call.

        Args:
            resource_ids: list of int resource IDs.

        Returns:
            dict {resource_id: {"buy_1": int, "sell_1": int}}
            Missing pools are omitted.
        """
        from blockchain.xrpl.xrpl_amm import get_multi_pool_prices

        # Map resource_id → currency_code
        currency_codes = []
        id_by_code = {}
        for rid in resource_ids:
            code = get_currency_code(rid)
            if code:
                currency_codes.append(code)
                id_by_code[code] = rid

        if not currency_codes:
            return {}

        raw = get_multi_pool_prices(currency_codes)

        # Re-key by resource_id
        result = {}
        for code, prices in raw.items():
            rid = id_by_code.get(code)
            if rid is not None:
                result[rid] = prices

        return result

    # ================================================================== #
    #  Buy resource (gold → resource)
    # ================================================================== #

    @staticmethod
    def buy_resource(wallet_address, character_key, resource_id, amount,
                     gold_cost, vault_address):
        """
        Buy a resource from the AMM pool using gold.

        Flow:
            1. Execute on-chain swap (vault sends FCMGold, receives resource)
            2. Update game state atomically:
               - CHARACTER gold → RESERVE (player pays gold)
               - RESERVE resource → CHARACTER (player receives resource)

        Args:
            wallet_address: Player's wallet address.
            character_key: Player's character key.
            resource_id: int resource ID to buy.
            amount: int amount of resource to buy.
            gold_cost: int gold cost (pre-rounded ceiling).
            vault_address: Vault wallet address.

        Returns:
            dict {gold_cost, resource_amount, tx_hash}

        Raises:
            XRPLTransactionError if the on-chain swap fails.
            ValueError if resource_id is unknown.
        """
        from blockchain.xrpl.xrpl_amm import execute_swap

        gold_currency = settings.XRPL_GOLD_CURRENCY_CODE
        resource_currency = get_currency_code(resource_id)
        if not resource_currency:
            raise ValueError(f"Unknown resource_id: {resource_id}")

        # 1. Execute on-chain swap
        swap_result = execute_swap(
            from_currency=gold_currency,
            to_currency=resource_currency,
            max_input=gold_cost,
            expected_output=amount,
        )
        actual_gold_spent = swap_result["actual_input"]
        actual_resource_received = swap_result["actual_output"]

        # 2. Update game state atomically
        #
        # Six operations — player side (integers) + AMM side (decimals):
        #   Player pays gold_cost gold → CHARACTER gold -N
        #   Gold enters vault → RESERVE gold +N
        #   Vault pays AMM → RESERVE gold -actual_gold_spent
        #   AMM returns resource → RESERVE resource +actual_resource_received
        #   Vault gives player resource → RESERVE resource -amount
        #   Player receives resource → CHARACTER resource +amount
        #
        # Net RESERVE gold: +(gold_cost - actual_gold_spent) = margin
        # Net RESERVE resource: +(actual_resource_received - amount) = surplus
        with transaction.atomic():
            # Player pays gold
            FungibleService._debit(
                gold_currency, Decimal(gold_cost),
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleService._credit(
                gold_currency, Decimal(gold_cost),
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # Vault pays AMM (actual decimal amount)
            FungibleService._debit(
                gold_currency, actual_gold_spent,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # AMM returns resource (actual decimal amount)
            FungibleService._credit(
                resource_currency, actual_resource_received,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # Vault gives player resource
            FungibleService._debit(
                resource_currency, Decimal(amount),
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleService._credit(
                resource_currency, Decimal(amount),
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )

            # Transfer logs — player side
            FungibleTransferLog.objects.create(
                currency_code=gold_currency,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=Decimal(gold_cost),
                transfer_type="amm_buy",
            )
            FungibleTransferLog.objects.create(
                currency_code=resource_currency,
                from_wallet=vault_address,
                to_wallet=wallet_address,
                amount=Decimal(amount),
                transfer_type="amm_buy",
            )
            # Transfer logs — AMM side (actual on-chain amounts)
            FungibleTransferLog.objects.create(
                currency_code=gold_currency,
                from_wallet=vault_address,
                to_wallet="AMM_POOL",
                amount=actual_gold_spent,
                transfer_type="amm_swap",
            )
            FungibleTransferLog.objects.create(
                currency_code=resource_currency,
                from_wallet="AMM_POOL",
                to_wallet=vault_address,
                amount=actual_resource_received,
                transfer_type="amm_swap",
            )

            # Transaction log for reconciliation
            XRPLTransactionLog.objects.create(
                tx_hash=swap_result["tx_hash"],
                tx_type="amm_buy",
                currency_code=resource_currency,
                amount=Decimal(amount),
                wallet_address=wallet_address,
                status="confirmed",
            )

        margin = Decimal(gold_cost) - actual_gold_spent
        resource_dust = actual_resource_received - Decimal(amount)

        # Move rounding dust from RESERVE → SINK
        if margin > 0 or resource_dust > 0:
            with transaction.atomic():
                if margin > 0:
                    FungibleService._debit(
                        gold_currency, margin,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_RESERVE,
                    )
                    FungibleService._credit(
                        gold_currency, margin,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_SINK,
                    )
                if resource_dust > 0:
                    FungibleService._debit(
                        resource_currency, resource_dust,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_RESERVE,
                    )
                    FungibleService._credit(
                        resource_currency, resource_dust,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_SINK,
                    )

        logger.info(
            f"AMM Buy: {wallet_address} bought {amount} {resource_currency} "
            f"for {gold_cost} gold (actual cost: {actual_gold_spent}, "
            f"gold dust: {margin}, resource dust: {resource_dust}) "
            f"(tx: {swap_result['tx_hash']})"
        )

        return {
            "gold_cost": gold_cost,
            "resource_amount": amount,
            "tx_hash": swap_result["tx_hash"],
            "actual_gold_spent": actual_gold_spent,
            "actual_resource_received": actual_resource_received,
            "gold_dust": margin,
            "resource_dust": resource_dust,
        }

    # ================================================================== #
    #  Sell resource (resource → gold)
    # ================================================================== #

    @staticmethod
    def sell_resource(wallet_address, character_key, resource_id, amount,
                      gold_received, vault_address):
        """
        Sell a resource to the AMM pool for gold.

        Flow:
            1. Execute on-chain swap (vault sends resource, receives FCMGold)
            2. Update game state atomically:
               - CHARACTER resource → RESERVE (player gives up resource)
               - RESERVE gold → CHARACTER (player receives gold)

        Args:
            wallet_address: Player's wallet address.
            character_key: Player's character key.
            resource_id: int resource ID to sell.
            amount: int amount of resource to sell.
            gold_received: int gold received (pre-rounded floor).
            vault_address: Vault wallet address.

        Returns:
            dict {gold_received, resource_amount, tx_hash}

        Raises:
            XRPLTransactionError if the on-chain swap fails.
            ValueError if resource_id is unknown.
        """
        from blockchain.xrpl.xrpl_amm import execute_swap

        gold_currency = settings.XRPL_GOLD_CURRENCY_CODE
        resource_currency = get_currency_code(resource_id)
        if not resource_currency:
            raise ValueError(f"Unknown resource_id: {resource_id}")

        # 1. Execute on-chain swap
        swap_result = execute_swap(
            from_currency=resource_currency,
            to_currency=gold_currency,
            max_input=amount,
            expected_output=gold_received,
        )
        actual_resource_spent = swap_result["actual_input"]
        actual_gold_received = swap_result["actual_output"]

        # 2. Update game state atomically
        #
        # Six operations — player side (integers) + AMM side (decimals):
        #   Player gives resource → CHARACTER resource -amount
        #   Resource enters vault → RESERVE resource +amount
        #   Vault pays AMM resource → RESERVE resource -actual_resource_spent
        #   AMM returns gold → RESERVE gold +actual_gold_received
        #   Vault gives player gold → RESERVE gold -gold_received
        #   Player receives gold → CHARACTER gold +gold_received
        #
        # Net RESERVE resource: +(amount - actual_resource_spent) = surplus
        # Net RESERVE gold: +(actual_gold_received - gold_received) = margin
        with transaction.atomic():
            # Player gives resource
            FungibleService._debit(
                resource_currency, Decimal(amount),
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleService._credit(
                resource_currency, Decimal(amount),
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # Vault pays AMM resource (actual decimal amount)
            FungibleService._debit(
                resource_currency, actual_resource_spent,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # AMM returns gold (actual decimal amount)
            FungibleService._credit(
                gold_currency, actual_gold_received,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # Vault gives player gold
            FungibleService._debit(
                gold_currency, Decimal(gold_received),
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleService._credit(
                gold_currency, Decimal(gold_received),
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )

            # Transfer logs — player side
            FungibleTransferLog.objects.create(
                currency_code=resource_currency,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=Decimal(amount),
                transfer_type="amm_sell",
            )
            FungibleTransferLog.objects.create(
                currency_code=gold_currency,
                from_wallet=vault_address,
                to_wallet=wallet_address,
                amount=Decimal(gold_received),
                transfer_type="amm_sell",
            )
            # Transfer logs — AMM side (actual on-chain amounts)
            FungibleTransferLog.objects.create(
                currency_code=resource_currency,
                from_wallet=vault_address,
                to_wallet="AMM_POOL",
                amount=actual_resource_spent,
                transfer_type="amm_swap",
            )
            FungibleTransferLog.objects.create(
                currency_code=gold_currency,
                from_wallet="AMM_POOL",
                to_wallet=vault_address,
                amount=actual_gold_received,
                transfer_type="amm_swap",
            )

            # Transaction log for reconciliation
            XRPLTransactionLog.objects.create(
                tx_hash=swap_result["tx_hash"],
                tx_type="amm_sell",
                currency_code=resource_currency,
                amount=Decimal(amount),
                wallet_address=wallet_address,
                status="confirmed",
            )

        margin = actual_gold_received - Decimal(gold_received)
        resource_dust = Decimal(amount) - actual_resource_spent

        # Move rounding dust from RESERVE → SINK
        if margin > 0 or resource_dust > 0:
            with transaction.atomic():
                if margin > 0:
                    FungibleService._debit(
                        gold_currency, margin,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_RESERVE,
                    )
                    FungibleService._credit(
                        gold_currency, margin,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_SINK,
                    )
                if resource_dust > 0:
                    FungibleService._debit(
                        resource_currency, resource_dust,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_RESERVE,
                    )
                    FungibleService._credit(
                        resource_currency, resource_dust,
                        wallet_address=vault_address,
                        location=FungibleGameState.LOCATION_SINK,
                    )

        logger.info(
            f"AMM Sell: {wallet_address} sold {amount} {resource_currency} "
            f"for {gold_received} gold (actual received: {actual_gold_received}, "
            f"gold dust: {margin}, resource dust: {resource_dust}) "
            f"(tx: {swap_result['tx_hash']})"
        )

        return {
            "gold_received": gold_received,
            "resource_amount": amount,
            "tx_hash": swap_result["tx_hash"],
            "actual_resource_spent": actual_resource_spent,
            "actual_gold_received": actual_gold_received,
            "gold_dust": margin,
            "resource_dust": resource_dust,
        }
