"""
ResourceService — game-side operations for FCMResources on XRPL.

Same interface as Polygon's ResourceService. Accepts chain_id,
contract_address, vault_address params but ignores chain_id and
contract_address. Maps resource_id -> currency_code via CurrencyType
lookup (cached).

Delegates all operations to FungibleService with the mapped currency_code.
"""

from decimal import Decimal

from blockchain.xrpl.currency_cache import get_currency_code
from blockchain.xrpl.models import FungibleGameState
from blockchain.xrpl.services.fungible import FungibleService


def _code(resource_id):
    """Map resource_id to XRPL currency_code, or raise."""
    code = get_currency_code(resource_id)
    if code is None:
        raise ValueError(f"Unknown resource_id: {resource_id}")
    return code


class ResourceService:
    """Service layer for all in-game resource operations (XRPL)."""

    # ================================================================== #
    #  Queries
    # ================================================================== #

    @staticmethod
    def get_character_resource(wallet_address, resource_id, chain_id,
                               contract_address, character_key):
        return FungibleService.get_balance(
            _code(resource_id), wallet_address,
            FungibleGameState.LOCATION_CHARACTER, character_key,
        )

    @staticmethod
    def get_all_character_resources(wallet_address, chain_id,
                                    contract_address, character_key):
        return FungibleService.get_all_balances(
            None, wallet_address,
            FungibleGameState.LOCATION_CHARACTER, character_key,
        )

    @staticmethod
    def get_account_resource(wallet_address, resource_id, chain_id,
                             contract_address):
        return FungibleService.get_balance(
            _code(resource_id), wallet_address,
            FungibleGameState.LOCATION_ACCOUNT,
        )

    @staticmethod
    def get_chain_balance(wallet_address, resource_id, chain_id,
                          contract_address):
        """On XRPL, query the ledger directly. Stub returns 0 for now."""
        return Decimal(0)

    # ================================================================== #
    #  1. RESERVE <-> SPAWNED
    # ================================================================== #

    @staticmethod
    def spawn(resource_id, amount, chain_id, contract_address,
              vault_address):
        FungibleService.spawn(_code(resource_id), amount, vault_address)

    @staticmethod
    def despawn(resource_id, amount, chain_id, contract_address,
                vault_address):
        FungibleService.despawn(_code(resource_id), amount, vault_address)

    # ================================================================== #
    #  2. SPAWNED <-> CHARACTER
    # ================================================================== #

    @staticmethod
    def pickup(wallet_address, resource_id, amount, chain_id,
               contract_address, vault_address, character_key):
        FungibleService.pickup(
            _code(resource_id), wallet_address, amount,
            vault_address, character_key,
        )

    @staticmethod
    def drop(wallet_address, resource_id, amount, chain_id,
             contract_address, vault_address, character_key):
        FungibleService.drop(
            _code(resource_id), wallet_address, amount,
            vault_address, character_key,
        )

    # ================================================================== #
    #  3. CHARACTER <-> ACCOUNT
    # ================================================================== #

    @staticmethod
    def bank(wallet_address, resource_id, amount, chain_id,
             contract_address, character_key):
        FungibleService.bank(
            _code(resource_id), wallet_address, amount, character_key,
        )

    @staticmethod
    def unbank(wallet_address, resource_id, amount, chain_id,
               contract_address, character_key):
        FungibleService.unbank(
            _code(resource_id), wallet_address, amount, character_key,
        )

    # ================================================================== #
    #  4. ACCOUNT <-> chain
    # ================================================================== #

    @staticmethod
    def deposit_from_chain(wallet_address, resource_id, amount,
                           vault_address, tx_hash):
        FungibleService.deposit_from_chain(
            _code(resource_id), wallet_address, amount,
            vault_address, tx_hash,
        )

    @staticmethod
    def withdraw_to_chain(wallet_address, resource_id, amount,
                          vault_address, tx_hash):
        FungibleService.withdraw_to_chain(
            _code(resource_id), wallet_address, amount,
            vault_address, tx_hash,
        )

    # ================================================================== #
    #  5. CHARACTER <-> CHARACTER
    # ================================================================== #

    @staticmethod
    def transfer(from_wallet, from_character_key, to_wallet,
                 to_character_key, resource_id, amount, chain_id,
                 contract_address, transfer_type="trade"):
        FungibleService.transfer(
            _code(resource_id), from_wallet, from_character_key,
            to_wallet, to_character_key, amount, transfer_type,
        )

    # ================================================================== #
    #  6. CHARACTER <-> RESERVE (crafting)
    # ================================================================== #

    @staticmethod
    def craft_input(wallet_address, resource_id, amount, chain_id,
                    contract_address, vault_address, character_key):
        FungibleService.craft_input(
            _code(resource_id), wallet_address, amount,
            vault_address, character_key,
        )

    @staticmethod
    def craft_output(wallet_address, resource_id, amount, chain_id,
                     contract_address, vault_address, character_key):
        FungibleService.craft_output(
            _code(resource_id), wallet_address, amount,
            vault_address, character_key,
        )

    # ================================================================== #
    #  6b. * -> SINK (consumption / fees / dust)
    # ================================================================== #

    @staticmethod
    def sink(wallet_address, resource_id, amount, chain_id,
             contract_address, vault_address, character_key):
        FungibleService.sink(
            _code(resource_id), wallet_address, amount,
            vault_address, character_key,
        )

    @staticmethod
    def sink_world(resource_id, amount, chain_id, contract_address,
                   vault_address):
        """DISABLED: See FungibleService.sink_world() for details."""
        raise NotImplementedError(
            "ResourceService.sink_world() is not yet implemented. "
            "See FungibleService.sink_world() for details."
        )
        # --- Original implementation (disabled) ---
        # FungibleService.sink_world(
        #     _code(resource_id), amount, vault_address,
        # )

    @staticmethod
    def sink_account(wallet_address, resource_id, amount, chain_id,
                     contract_address, vault_address):
        FungibleService.sink_account(
            _code(resource_id), wallet_address, amount, vault_address,
        )

    # ================================================================== #
    #  7. RESERVE <-> ACCOUNT
    # ================================================================== #

    @staticmethod
    def reserve_to_account(wallet_address, resource_id, amount, chain_id,
                           contract_address, vault_address):
        FungibleService.reserve_to_account(
            _code(resource_id), wallet_address, amount, vault_address,
        )

    @staticmethod
    def account_to_reserve(wallet_address, resource_id, amount, chain_id,
                           contract_address, vault_address):
        FungibleService.account_to_reserve(
            _code(resource_id), wallet_address, amount, vault_address,
        )
