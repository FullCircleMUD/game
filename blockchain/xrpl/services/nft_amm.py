"""
NFTAMMService — game-level AMM buy/sell operations for NFT proxy tokens.

Bridges the XRPL AMM pool queries (xrpl_amm.py) with the game's
FungibleService state management. Uses PGold as the pair currency
(not FCMGold) to keep the NFT AMM market completely isolated.

Players never see PGold or proxy tokens — they pay/receive FCMGold.
The 1:1 PGold=FCMGold equivalence is a design invariant enforced here.

Game code should NOT import this directly — use the NFT shopkeeper
command set which calls this service via deferToThread.
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

logger = logging.getLogger("evennia")


class NFTAMMService:
    """Game-level AMM operations for buying and selling NFT items via proxy tokens."""

    # ================================================================== #
    #  Price queries
    # ================================================================== #

    @staticmethod
    def get_buy_price(tracking_token):
        """
        Get the gold cost to buy 1 NFT item from the AMM.

        Returns:
            int — gold cost, ceil-rounded (always rounds in game's favor).

        Raises:
            ValueError if pool doesn't exist or can't fill the order.
        """
        from blockchain.xrpl.xrpl_amm import get_swap_quote

        pgold = settings.XRPL_PGOLD_CURRENCY_CODE
        quote = get_swap_quote(
            tracking_token, 1, direction="buy", gold_currency=pgold,
        )
        return quote["gold_cost_rounded"]

    @staticmethod
    def get_sell_price(tracking_token):
        """
        Get the gold received from selling 1 NFT item to the AMM.

        Returns:
            int — gold received, floor-rounded (always rounds in game's favor).

        Raises:
            ValueError if pool doesn't exist.
        """
        from blockchain.xrpl.xrpl_amm import get_swap_quote

        pgold = settings.XRPL_PGOLD_CURRENCY_CODE
        quote = get_swap_quote(
            tracking_token, 1, direction="sell", gold_currency=pgold,
        )
        return quote["gold_received_rounded"]

    @staticmethod
    def get_pool_prices(tracking_tokens):
        """
        Get buy/sell prices for multiple proxy token pools in a single call.

        Args:
            tracking_tokens: list of tracking token currency codes.

        Returns:
            dict {tracking_token: {"buy_1": int, "sell_1": int}}
            Missing pools are omitted.
        """
        from blockchain.xrpl.xrpl_amm import get_multi_pool_prices

        pgold = settings.XRPL_PGOLD_CURRENCY_CODE
        return get_multi_pool_prices(tracking_tokens, gold_currency=pgold)

    # ================================================================== #
    #  Buy item (player pays FCMGold, vault buys proxy token from AMM)
    # ================================================================== #

    @staticmethod
    def buy_item(wallet_address, character_key, tracking_token,
                 gold_cost, vault_address):
        """
        Buy 1 NFT item from the AMM via proxy token.

        On-chain: vault spends PGold, receives 1 proxy token from AMM.
        Game state:
            1. Player pays gold_cost FCMGold (CHARACTER → RESERVE)
            2. Vault PGold RESERVE debited by actual_pgold_spent
            3. Gold margin (gold_cost - actual_pgold_spent) → SINK
            4. Transfer + transaction logs

        Args:
            wallet_address: Player's wallet address.
            character_key: Player's character key.
            tracking_token: Proxy token currency code (e.g. "PTrainDagger").
            gold_cost: int gold cost (pre-rounded ceiling).
            vault_address: Vault wallet address.

        Returns:
            dict {gold_cost, tx_hash, actual_pgold_spent, gold_dust}

        Raises:
            XRPLTransactionError if the on-chain swap fails.
        """
        from blockchain.xrpl.xrpl_amm import execute_swap

        fcm_gold = settings.XRPL_GOLD_CURRENCY_CODE
        pgold = settings.XRPL_PGOLD_CURRENCY_CODE

        # 1. Execute on-chain swap: vault sends PGold, receives proxy token
        swap_result = execute_swap(
            from_currency=pgold,
            to_currency=tracking_token,
            max_input=gold_cost,
            expected_output=1,
        )
        actual_pgold_spent = swap_result["actual_input"]

        # 2. Update game state atomically
        #
        # Player side (FCMGold integers):
        #   CHARACTER FCMGold -gold_cost (player pays)
        #   RESERVE FCMGold +gold_cost (vault receives)
        #
        # Vault side (PGold decimals):
        #   RESERVE PGold -actual_pgold_spent (vault spent to AMM)
        #
        # Net RESERVE FCMGold: +gold_cost
        # Net RESERVE PGold: -actual_pgold_spent
        # Margin: gold_cost - actual_pgold_spent (always >= 0 due to ceil)
        with transaction.atomic():
            # Player pays FCMGold
            FungibleService._debit(
                fcm_gold, Decimal(gold_cost),
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleService._credit(
                fcm_gold, Decimal(gold_cost),
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # Vault PGold decreases (spent to AMM)
            FungibleService._debit(
                pgold, actual_pgold_spent,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )

            # Transfer logs — player side
            FungibleTransferLog.objects.create(
                currency_code=fcm_gold,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=Decimal(gold_cost),
                transfer_type="nft_amm_buy",
            )
            # Transfer logs — AMM side
            FungibleTransferLog.objects.create(
                currency_code=pgold,
                from_wallet=vault_address,
                to_wallet="AMM_POOL",
                amount=actual_pgold_spent,
                transfer_type="nft_amm_swap",
            )
            FungibleTransferLog.objects.create(
                currency_code=tracking_token,
                from_wallet="AMM_POOL",
                to_wallet=vault_address,
                amount=Decimal(1),
                transfer_type="nft_amm_swap",
            )

            # Transaction log
            XRPLTransactionLog.objects.create(
                tx_hash=swap_result["tx_hash"],
                tx_type="nft_amm_buy",
                currency_code=tracking_token,
                amount=Decimal(1),
                wallet_address=wallet_address,
                status="confirmed",
            )

        # Move rounding dust from RESERVE → SINK
        margin = Decimal(gold_cost) - actual_pgold_spent
        if margin > 0:
            with transaction.atomic():
                FungibleService._debit(
                    fcm_gold, margin,
                    wallet_address=vault_address,
                    location=FungibleGameState.LOCATION_RESERVE,
                )
                FungibleService._credit(
                    fcm_gold, margin,
                    wallet_address=vault_address,
                    location=FungibleGameState.LOCATION_SINK,
                )

        logger.info(
            f"NFT AMM Buy: {wallet_address} bought 1 {tracking_token} "
            f"for {gold_cost} gold (actual PGold spent: {actual_pgold_spent}, "
            f"gold dust: {margin}) (tx: {swap_result['tx_hash']})"
        )

        return {
            "gold_cost": gold_cost,
            "tx_hash": swap_result["tx_hash"],
            "actual_pgold_spent": actual_pgold_spent,
            "gold_dust": margin,
        }

    # ================================================================== #
    #  Sell item (player receives FCMGold, vault sells proxy token to AMM)
    # ================================================================== #

    @staticmethod
    def sell_item(wallet_address, character_key, tracking_token,
                  gold_received, vault_address):
        """
        Sell 1 NFT item to the AMM via proxy token.

        On-chain: vault sends 1 proxy token, receives PGold from AMM.
        Game state:
            1. Vault PGold RESERVE credited by actual_pgold_received
            2. Vault FCMGold RESERVE debited by gold_received (pay player)
            3. Player receives gold_received FCMGold (RESERVE → CHARACTER)
            4. PGold margin (actual_pgold_received - gold_received) → SINK
            5. Transfer + transaction logs

        Args:
            wallet_address: Player's wallet address.
            character_key: Player's character key.
            tracking_token: Proxy token currency code (e.g. "PTrainDagger").
            gold_received: int gold to pay player (pre-rounded floor).
            vault_address: Vault wallet address.

        Returns:
            dict {gold_received, tx_hash, actual_pgold_received, pgold_dust}

        Raises:
            XRPLTransactionError if the on-chain swap fails.
        """
        from blockchain.xrpl.xrpl_amm import execute_swap

        fcm_gold = settings.XRPL_GOLD_CURRENCY_CODE
        pgold = settings.XRPL_PGOLD_CURRENCY_CODE

        # 1. Execute on-chain swap: vault sends proxy token, receives PGold
        swap_result = execute_swap(
            from_currency=tracking_token,
            to_currency=pgold,
            max_input=1,
            expected_output=gold_received,
        )
        actual_pgold_received = swap_result["actual_output"]

        # 2. Update game state atomically
        #
        # Vault side (PGold):
        #   RESERVE PGold +actual_pgold_received (from AMM)
        #
        # Player side (FCMGold integers):
        #   RESERVE FCMGold -gold_received (vault pays)
        #   CHARACTER FCMGold +gold_received (player receives)
        #
        # Net RESERVE PGold: +actual_pgold_received
        # Net RESERVE FCMGold: -gold_received
        # Margin: actual_pgold_received - gold_received (always >= 0 due to floor)
        with transaction.atomic():
            # Vault PGold increases (received from AMM)
            FungibleService._credit(
                pgold, actual_pgold_received,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            # Vault pays player FCMGold
            FungibleService._debit(
                fcm_gold, Decimal(gold_received),
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleService._credit(
                fcm_gold, Decimal(gold_received),
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )

            # Transfer logs — AMM side
            FungibleTransferLog.objects.create(
                currency_code=tracking_token,
                from_wallet=vault_address,
                to_wallet="AMM_POOL",
                amount=Decimal(1),
                transfer_type="nft_amm_swap",
            )
            FungibleTransferLog.objects.create(
                currency_code=pgold,
                from_wallet="AMM_POOL",
                to_wallet=vault_address,
                amount=actual_pgold_received,
                transfer_type="nft_amm_swap",
            )
            # Transfer logs — player side
            FungibleTransferLog.objects.create(
                currency_code=fcm_gold,
                from_wallet=vault_address,
                to_wallet=wallet_address,
                amount=Decimal(gold_received),
                transfer_type="nft_amm_sell",
            )

            # Transaction log
            XRPLTransactionLog.objects.create(
                tx_hash=swap_result["tx_hash"],
                tx_type="nft_amm_sell",
                currency_code=tracking_token,
                amount=Decimal(1),
                wallet_address=wallet_address,
                status="confirmed",
            )

        # Move PGold rounding dust from RESERVE → SINK
        pgold_dust = actual_pgold_received - Decimal(gold_received)
        if pgold_dust > 0:
            with transaction.atomic():
                FungibleService._debit(
                    pgold, pgold_dust,
                    wallet_address=vault_address,
                    location=FungibleGameState.LOCATION_RESERVE,
                )
                FungibleService._credit(
                    pgold, pgold_dust,
                    wallet_address=vault_address,
                    location=FungibleGameState.LOCATION_SINK,
                )

        logger.info(
            f"NFT AMM Sell: {wallet_address} sold 1 {tracking_token} "
            f"for {gold_received} gold (actual PGold received: {actual_pgold_received}, "
            f"PGold dust: {pgold_dust}) (tx: {swap_result['tx_hash']})"
        )

        return {
            "gold_received": gold_received,
            "tx_hash": swap_result["tx_hash"],
            "actual_pgold_received": actual_pgold_received,
            "pgold_dust": pgold_dust,
        }
