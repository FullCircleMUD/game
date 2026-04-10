"""
GoldService — game-side operations for FCMGold on XRPL.

Delegates all operations to FungibleService with currency_code="FCMGold".
"""

from decimal import Decimal

from django.conf import settings

from blockchain.xrpl.models import FungibleGameState
from blockchain.xrpl.services.fungible import FungibleService

GOLD_CURRENCY_CODE = getattr(settings, "XRPL_GOLD_CURRENCY_CODE", "FCMGold")


class GoldService:
    """Service layer for all in-game gold operations (XRPL)."""

    # ================================================================== #
    #  Queries
    # ================================================================== #

    @staticmethod
    def get_character_gold(wallet_address, character_key):
        return FungibleService.get_balance(
            GOLD_CURRENCY_CODE, wallet_address,
            FungibleGameState.LOCATION_CHARACTER, character_key,
        )

    @staticmethod
    def get_account_gold(wallet_address):
        return FungibleService.get_balance(
            GOLD_CURRENCY_CODE, wallet_address,
            FungibleGameState.LOCATION_ACCOUNT,
        )

    @staticmethod
    def get_reserve_balance(vault_address):
        return FungibleService.get_balance(
            GOLD_CURRENCY_CODE, vault_address,
            FungibleGameState.LOCATION_RESERVE,
        )

    @staticmethod
    def get_spawned_balance(vault_address):
        return FungibleService.get_balance(
            GOLD_CURRENCY_CODE, vault_address,
            FungibleGameState.LOCATION_SPAWNED,
        )

    @staticmethod
    def get_chain_balance(wallet_address):
        """On XRPL, query the ledger directly. Stub returns 0 for now."""
        return Decimal(0)

    # ================================================================== #
    #  1. RESERVE <-> SPAWNED
    # ================================================================== #

    @staticmethod
    def spawn(amount, vault_address):
        FungibleService.spawn(GOLD_CURRENCY_CODE, amount, vault_address)

    @staticmethod
    def despawn(amount, vault_address):
        FungibleService.despawn(GOLD_CURRENCY_CODE, amount, vault_address)

    # ================================================================== #
    #  2. SPAWNED <-> CHARACTER
    # ================================================================== #

    @staticmethod
    def pickup(wallet_address, amount, vault_address, character_key):
        FungibleService.pickup(
            GOLD_CURRENCY_CODE, wallet_address, amount,
            vault_address, character_key,
        )

    @staticmethod
    def drop(wallet_address, amount, vault_address, character_key):
        FungibleService.drop(
            GOLD_CURRENCY_CODE, wallet_address, amount,
            vault_address, character_key,
        )

    # ================================================================== #
    #  3. CHARACTER <-> ACCOUNT
    # ================================================================== #

    @staticmethod
    def bank(wallet_address, amount, character_key):
        FungibleService.bank(
            GOLD_CURRENCY_CODE, wallet_address, amount, character_key,
        )

    @staticmethod
    def unbank(wallet_address, amount, character_key):
        FungibleService.unbank(
            GOLD_CURRENCY_CODE, wallet_address, amount, character_key,
        )

    # ================================================================== #
    #  4. ACCOUNT <-> chain
    # ================================================================== #

    @staticmethod
    def deposit_from_chain(wallet_address, amount, vault_address, tx_hash):
        FungibleService.deposit_from_chain(
            GOLD_CURRENCY_CODE, wallet_address, amount,
            vault_address, tx_hash,
        )

    @staticmethod
    def withdraw_to_chain(wallet_address, amount, vault_address, tx_hash):
        FungibleService.withdraw_to_chain(
            GOLD_CURRENCY_CODE, wallet_address, amount,
            vault_address, tx_hash,
        )

    # ================================================================== #
    #  5. CHARACTER <-> CHARACTER
    # ================================================================== #

    @staticmethod
    def transfer(from_wallet, from_character_key, to_wallet,
                 to_character_key, amount, transfer_type="trade"):
        FungibleService.transfer(
            GOLD_CURRENCY_CODE, from_wallet, from_character_key,
            to_wallet, to_character_key, amount, transfer_type,
        )

    # ================================================================== #
    #  6. CHARACTER <-> RESERVE (crafting)
    # ================================================================== #

    @staticmethod
    def craft_input(wallet_address, amount, vault_address, character_key):
        FungibleService.craft_input(
            GOLD_CURRENCY_CODE, wallet_address, amount,
            vault_address, character_key,
        )

    @staticmethod
    def sink(wallet_address, amount, vault_address, character_key):
        FungibleService.sink(
            GOLD_CURRENCY_CODE, wallet_address, amount,
            vault_address, character_key,
        )

    @staticmethod
    def sink_world(amount, vault_address):
        """DISABLED: See FungibleService.sink_world() for details."""
        raise NotImplementedError(
            "GoldService.sink_world() is not yet implemented. "
            "See FungibleService.sink_world() for details."
        )

    @staticmethod
    def sink_account(wallet_address, amount, vault_address):
        FungibleService.sink_account(
            GOLD_CURRENCY_CODE, wallet_address, amount, vault_address,
        )

    @staticmethod
    def craft_output(wallet_address, amount, vault_address, character_key):
        FungibleService.craft_output(
            GOLD_CURRENCY_CODE, wallet_address, amount,
            vault_address, character_key,
        )

    # ================================================================== #
    #  7. RESERVE <-> ACCOUNT
    # ================================================================== #

    @staticmethod
    def reserve_to_account(wallet_address, amount, vault_address):
        FungibleService.reserve_to_account(
            GOLD_CURRENCY_CODE, wallet_address, amount, vault_address,
        )

    @staticmethod
    def account_to_reserve(wallet_address, amount, vault_address):
        FungibleService.account_to_reserve(
            GOLD_CURRENCY_CODE, wallet_address, amount, vault_address,
        )
