"""
FungibleService — core game-side operations for all XRPL issued currencies.

This is the internal engine that GoldService and ResourceService delegate to.
Do not import this directly from game code — use GoldService or ResourceService.

All vault-held currencies are tracked in FungibleGameState rows with
location-based subdivisions. The vault (game/bridge wallet) holds all
game-owned assets. No chain state mirror — the game queries XRPL directly
when needed.

Zero-balance rows are deleted, not kept (balance > 0 constraint).
All writes wrapped in transaction.atomic() for ACID guarantees.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import F

from blockchain.xrpl.models import (
    FungibleGameState,
    FungibleTransferLog,
    XRPLTransactionLog,
)


class FungibleService:
    """Core service for all fungible currency operations on XRPL."""

    # ================================================================== #
    #  Private helpers
    # ================================================================== #

    @staticmethod
    def _debit(currency_code, amount, **kwargs):
        """
        Subtract amount from a FungibleGameState row matched by kwargs.
        Deletes row if balance reaches 0 (satisfies balance > 0 constraint).
        Raises ValueError if row missing or insufficient balance.
        Must be called inside transaction.atomic().
        """
        try:
            row = FungibleGameState.objects.select_for_update().get(
                currency_code=currency_code,
                **kwargs,
            )
        except FungibleGameState.DoesNotExist:
            raise ValueError(
                f"No fungible game state row for {currency_code} {kwargs}"
            )

        if row.balance < amount:
            raise ValueError(
                f"Insufficient {currency_code}: have {row.balance}, need {amount}"
            )

        if row.balance == amount:
            row.delete()
        else:
            row.balance -= amount
            row.save(update_fields=["balance", "updated_at"])

    @staticmethod
    def _credit(currency_code, amount, **kwargs):
        """
        Add amount to a FungibleGameState row. Creates row if not exists.
        Must be called inside transaction.atomic().
        """
        row, created = FungibleGameState.objects.get_or_create(
            currency_code=currency_code,
            **kwargs,
            defaults={"balance": amount},
        )
        if not created:
            FungibleGameState.objects.filter(pk=row.pk).update(
                balance=F("balance") + amount
            )

    # ================================================================== #
    #  Queries
    # ================================================================== #

    @staticmethod
    def get_balance(currency_code, wallet_address, location, character_key=None):
        """Returns balance for a specific location, or 0."""
        filters = {
            "currency_code": currency_code,
            "wallet_address": wallet_address,
            "location": location,
        }
        if character_key is not None:
            filters["character_key"] = character_key
        try:
            row = FungibleGameState.objects.get(**filters)
            return row.balance
        except FungibleGameState.DoesNotExist:
            return Decimal(0)

    @staticmethod
    def get_all_balances(currency_code, wallet_address, location,
                         character_key=None):
        """Returns queryset of matching FungibleGameState rows."""
        filters = {
            "wallet_address": wallet_address,
            "location": location,
        }
        if currency_code is not None:
            filters["currency_code"] = currency_code
        if character_key is not None:
            filters["character_key"] = character_key
        return FungibleGameState.objects.filter(**filters)

    # ================================================================== #
    #  1. RESERVE <-> SPAWNED (vault-internal, not logged)
    # ================================================================== #

    @staticmethod
    def spawn(currency_code, amount, vault_address):
        """
        Currency enters the game world (placed on mob, chest, room).
        RESERVE -> SPAWNED. Issuer-internal — not logged.
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SPAWNED,
            )

    @staticmethod
    def despawn(currency_code, amount, vault_address):
        """
        Currency leaves the game world unlooted (mob despawns, room deleted).
        SPAWNED -> RESERVE. Issuer-internal — not logged.
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SPAWNED,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )

    # ================================================================== #
    #  2. SPAWNED <-> CHARACTER (character loots / drops)
    # ================================================================== #

    @staticmethod
    def pickup(currency_code, wallet_address, amount, vault_address,
               character_key):
        """
        Character picks up currency from the game world.
        SPAWNED (vault) -> CHARACTER (player).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SPAWNED,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=vault_address,
                to_wallet=wallet_address,
                amount=amount,
                transfer_type="pickup",
            )

    @staticmethod
    def drop(currency_code, wallet_address, amount, vault_address,
             character_key):
        """
        Character drops currency on the ground.
        CHARACTER (player) -> SPAWNED (vault).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SPAWNED,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="drop",
            )

    # ================================================================== #
    #  3. CHARACTER <-> ACCOUNT (bank / unbank)
    # ================================================================== #

    @staticmethod
    def bank(currency_code, wallet_address, amount, character_key):
        """
        Character deposits currency into their bank account.
        CHARACTER -> ACCOUNT. Same wallet, different location.
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_ACCOUNT,
            )

    @staticmethod
    def unbank(currency_code, wallet_address, amount, character_key):
        """
        Character withdraws currency from their bank account.
        ACCOUNT -> CHARACTER. Same wallet, different location.
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_ACCOUNT,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )

    # ================================================================== #
    #  4. ACCOUNT <-> chain (deposit to game / withdraw from game)
    # ================================================================== #

    @staticmethod
    def deposit_from_chain(currency_code, wallet_address, amount,
                           vault_address, tx_hash):
        """
        Player deposited currency on-chain to the vault.
        Credits player's ACCOUNT, debits vault's RESERVE.
        Stamps XRPLTransactionLog for dedup + crash recovery.

        Raises ValueError if tx_hash has already been processed.
        """
        with transaction.atomic():
            if XRPLTransactionLog.objects.filter(
                tx_hash=tx_hash, status="confirmed",
            ).exists():
                raise ValueError(
                    f"Transaction {tx_hash} already processed"
                )

            FungibleService._debit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_ACCOUNT,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=vault_address,
                to_wallet=wallet_address,
                amount=amount,
                transfer_type="deposit_from_chain",
            )
            XRPLTransactionLog.objects.create(
                tx_hash=tx_hash,
                tx_type="import",
                currency_code=currency_code,
                amount=amount,
                wallet_address=wallet_address,
                status="confirmed",
            )

    @staticmethod
    def withdraw_to_chain(currency_code, wallet_address, amount,
                          vault_address, tx_hash):
        """
        Player withdrawing currency from game to their XRPL wallet.
        Debits player's ACCOUNT, credits vault's RESERVE.
        Stamps XRPLTransactionLog for dedup + crash recovery.

        Raises ValueError if tx_hash has already been processed.
        """
        with transaction.atomic():
            if XRPLTransactionLog.objects.filter(
                tx_hash=tx_hash, status="confirmed",
            ).exists():
                raise ValueError(
                    f"Transaction {tx_hash} already processed"
                )

            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_ACCOUNT,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="withdraw_to_chain",
            )
            XRPLTransactionLog.objects.create(
                tx_hash=tx_hash,
                tx_type="export",
                currency_code=currency_code,
                amount=amount,
                wallet_address=wallet_address,
                status="confirmed",
            )

    # ================================================================== #
    #  5. CHARACTER <-> CHARACTER (transfer / trade)
    # ================================================================== #

    @staticmethod
    def transfer(currency_code, from_wallet, from_key, to_wallet, to_key,
                 amount, transfer_type="trade"):
        """
        In-game currency transfer between characters (trade, give).
        CHARACTER (sender) -> CHARACTER (receiver).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=from_wallet,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=from_key,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=to_wallet,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=to_key,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                amount=amount,
                transfer_type=transfer_type,
            )

    # ================================================================== #
    #  6. CHARACTER <-> RESERVE (crafting)
    # ================================================================== #

    @staticmethod
    def craft_input(currency_code, wallet_address, amount, vault_address,
                    character_key):
        """
        Crafting consumes currency from character.
        CHARACTER (player) -> RESERVE (vault).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="craft_input",
            )

    # ================================================================== #
    #  6b. * -> SINK (consumption / fees / dust)
    # ================================================================== #

    @staticmethod
    def sink(currency_code, wallet_address, amount, vault_address,
             character_key):
        """
        Consume currency from character into SINK.
        CHARACTER (player) -> SINK (vault).
        Used for: gold fees, crafting inputs, resource consumption, dust.
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SINK,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="sink",
            )

    @staticmethod
    def sink_world(currency_code, amount, vault_address):
        """
        Consume world-spawned currency into SINK.
        SPAWNED (world) -> SINK (vault).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SPAWNED,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SINK,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=vault_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="sink",
            )

    @staticmethod
    def sink_account(currency_code, wallet_address, amount, vault_address):
        """
        Consume currency from account into SINK.
        ACCOUNT (player) -> SINK (vault).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_ACCOUNT,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_SINK,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="sink",
            )

    @staticmethod
    def craft_output(currency_code, wallet_address, amount, vault_address,
                     character_key):
        """
        Crafting produces currency for character.
        RESERVE (vault) -> CHARACTER (player).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=vault_address,
                to_wallet=wallet_address,
                amount=amount,
                transfer_type="craft_output",
            )

    # ================================================================== #
    #  7. RESERVE <-> ACCOUNT (future-proofing)
    # ================================================================== #

    @staticmethod
    def reserve_to_account(currency_code, wallet_address, amount,
                           vault_address):
        """
        Move currency from vault reserve directly to a player's account.
        RESERVE (vault) -> ACCOUNT (player).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_ACCOUNT,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=vault_address,
                to_wallet=wallet_address,
                amount=amount,
                transfer_type="reserve_to_account",
            )

    @staticmethod
    def account_to_reserve(currency_code, wallet_address, amount,
                           vault_address):
        """
        Move currency from a player's account back to vault reserve.
        ACCOUNT (player) -> RESERVE (vault).
        """
        with transaction.atomic():
            FungibleService._debit(
                currency_code, amount,
                wallet_address=wallet_address,
                location=FungibleGameState.LOCATION_ACCOUNT,
            )
            FungibleService._credit(
                currency_code, amount,
                wallet_address=vault_address,
                location=FungibleGameState.LOCATION_RESERVE,
            )
            FungibleTransferLog.objects.create(
                currency_code=currency_code,
                from_wallet=wallet_address,
                to_wallet=vault_address,
                amount=amount,
                transfer_type="account_to_reserve",
            )
