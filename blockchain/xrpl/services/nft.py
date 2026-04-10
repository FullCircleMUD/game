"""
NFTService — game-side operations for XRPL NFTokens.

Each NFT is a single row in NFTGameState. Moves update location,
owner_in_game, and character_key.

All writes wrapped in transaction.atomic() for ACID guarantees.
"""

from django.db import transaction
from django.utils import timezone

from blockchain.xrpl.models import (
    NFTGameState,
    NFTItemType,
    NFTTransferLog,
    XRPLTransactionLog,
)


class NFTService:
    """Service layer for all in-game NFT operations (XRPL)."""

    # ================================================================== #
    #  Private helpers
    # ================================================================== #

    @staticmethod
    def _reset_token_identity(nft):
        """Wipe item identity from an NFTGameState instance (in memory)."""
        nft.item_type = None
        nft.metadata = {}

    # ================================================================== #
    #  Queries
    # ================================================================== #

    @staticmethod
    def get_nft(token_id):
        """Returns a single NFTGameState row, or raises DoesNotExist."""
        return NFTGameState.objects.get(nftoken_id=str(token_id))

    @staticmethod
    def get_character_nfts(wallet_address, character_key):
        return NFTGameState.objects.filter(
            owner_in_game=wallet_address,
            location=NFTGameState.LOCATION_CHARACTER,
            character_key=character_key,
        )

    @staticmethod
    def get_account_nfts(wallet_address):
        return NFTGameState.objects.filter(
            owner_in_game=wallet_address,
            location=NFTGameState.LOCATION_ACCOUNT,
        )

    @staticmethod
    def get_available_for_spawn(vault_address, item_type=None):
        qs = NFTGameState.objects.filter(
            owner_in_game=vault_address,
            location=NFTGameState.LOCATION_RESERVE,
        )
        if item_type is not None:
            qs = qs.filter(item_type=item_type)
        return qs

    # ================================================================== #
    #  0. BLANK POOL — assign identity to a reserve token
    # ================================================================== #

    @staticmethod
    def assign_item_type(item_type_name):
        item_type = NFTItemType.objects.get(name=item_type_name)

        with transaction.atomic():
            nft = (
                NFTGameState.objects
                .select_for_update()
                .filter(
                    location=NFTGameState.LOCATION_RESERVE,
                    item_type__isnull=True,
                )
                .order_by("nftoken_id")
                .first()
            )

            if nft is None:
                raise ValueError("No blank tokens available in reserve pool")

            nft.item_type = item_type
            nft.metadata = item_type.default_metadata or {}
            nft.save(update_fields=["item_type", "metadata", "updated_at"])

        return nft.nftoken_id

    # ================================================================== #
    #  1. RESERVE <-> SPAWNED
    # ================================================================== #

    @staticmethod
    def spawn(token_id):
        updated = NFTGameState.objects.filter(
            nftoken_id=str(token_id),
            location=NFTGameState.LOCATION_RESERVE,
        ).update(location=NFTGameState.LOCATION_SPAWNED)

        if not updated:
            raise ValueError(f"NFT {token_id} is not in RESERVE state")

    @staticmethod
    def despawn(token_id):
        updated = NFTGameState.objects.filter(
            nftoken_id=str(token_id),
            location=NFTGameState.LOCATION_SPAWNED,
        ).update(
            location=NFTGameState.LOCATION_RESERVE,
            item_type=None,
            metadata={},
        )

        if not updated:
            raise ValueError(f"NFT {token_id} is not in SPAWNED state")

    # ================================================================== #
    #  2. SPAWNED <-> CHARACTER
    # ================================================================== #

    @staticmethod
    def pickup(token_id, wallet_address, character_key):
        with transaction.atomic():
            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_SPAWNED:
                raise ValueError(
                    f"NFT {token_id} is not in SPAWNED state "
                    f"(current: {nft.location})"
                )

            old_owner = nft.owner_in_game
            nft.location = NFTGameState.LOCATION_CHARACTER
            nft.owner_in_game = wallet_address
            nft.character_key = character_key
            nft.save(update_fields=[
                "location", "owner_in_game", "character_key", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=old_owner,
                to_wallet=wallet_address,
                transfer_type="pickup",
            )

    @staticmethod
    def drop(token_id, vault_address):
        with transaction.atomic():
            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_CHARACTER:
                raise ValueError(
                    f"NFT {token_id} is not in CHARACTER state "
                    f"(current: {nft.location})"
                )

            old_owner = nft.owner_in_game
            nft.location = NFTGameState.LOCATION_SPAWNED
            nft.owner_in_game = vault_address
            nft.character_key = None
            nft.save(update_fields=[
                "location", "owner_in_game", "character_key", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=old_owner,
                to_wallet=vault_address,
                transfer_type="drop",
            )

    # ================================================================== #
    #  3. CHARACTER <-> ACCOUNT
    # ================================================================== #

    @staticmethod
    def bank(token_id):
        with transaction.atomic():
            updated = NFTGameState.objects.filter(
                nftoken_id=str(token_id),
                location=NFTGameState.LOCATION_CHARACTER,
            ).update(
                location=NFTGameState.LOCATION_ACCOUNT,
                character_key=None,
            )

            if not updated:
                raise ValueError(f"NFT {token_id} is not in CHARACTER state")

    @staticmethod
    def unbank(token_id, character_key):
        with transaction.atomic():
            updated = NFTGameState.objects.filter(
                nftoken_id=str(token_id),
                location=NFTGameState.LOCATION_ACCOUNT,
            ).update(
                location=NFTGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )

            if not updated:
                raise ValueError(f"NFT {token_id} is not in ACCOUNT state")

    # ================================================================== #
    #  4. ACCOUNT <-> ONCHAIN
    # ================================================================== #

    @staticmethod
    def deposit_from_chain(token_id, wallet_address, vault_address, tx_hash):
        """Raises ValueError if tx_hash already processed or NFT not ONCHAIN."""
        with transaction.atomic():
            if XRPLTransactionLog.objects.filter(
                tx_hash=tx_hash, status="confirmed",
            ).exists():
                raise ValueError(
                    f"Transaction {tx_hash} already processed"
                )

            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_ONCHAIN:
                raise ValueError(
                    f"NFT {token_id} is not in ONCHAIN state "
                    f"(current: {nft.location})"
                )

            nft.location = NFTGameState.LOCATION_ACCOUNT
            nft.owner_in_game = wallet_address
            nft.save(update_fields=[
                "location", "owner_in_game", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=vault_address,
                to_wallet=wallet_address,
                transfer_type="deposit_from_chain",
            )

            XRPLTransactionLog.objects.create(
                tx_hash=tx_hash,
                tx_type="nft_import",
                nftoken_id=str(token_id),
                wallet_address=wallet_address,
                status="confirmed",
            )

    @staticmethod
    def withdraw_to_chain(token_id, tx_hash):
        """Raises ValueError if tx_hash already processed or NFT not ACCOUNT."""
        with transaction.atomic():
            if XRPLTransactionLog.objects.filter(
                tx_hash=tx_hash, status="confirmed",
            ).exists():
                raise ValueError(
                    f"Transaction {tx_hash} already processed"
                )

            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_ACCOUNT:
                raise ValueError(
                    f"NFT {token_id} is not in ACCOUNT state "
                    f"(current: {nft.location})"
                )

            old_owner = nft.owner_in_game
            nft.location = NFTGameState.LOCATION_ONCHAIN
            nft.owner_in_game = None
            nft.save(update_fields=[
                "location", "owner_in_game", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=old_owner,
                to_wallet="ONCHAIN",
                transfer_type="withdraw_to_chain",
            )

            XRPLTransactionLog.objects.create(
                tx_hash=tx_hash,
                tx_type="nft_export",
                nftoken_id=str(token_id),
                wallet_address=old_owner,
                status="confirmed",
            )

    # ================================================================== #
    #  5. CHARACTER <-> CHARACTER
    # ================================================================== #

    @staticmethod
    def transfer(token_id, from_wallet, from_character_key,
                 to_wallet, to_character_key, transfer_type="trade"):
        with transaction.atomic():
            updated = NFTGameState.objects.filter(
                nftoken_id=str(token_id),
                location=NFTGameState.LOCATION_CHARACTER,
                owner_in_game=from_wallet,
                character_key=from_character_key,
            ).update(
                owner_in_game=to_wallet,
                character_key=to_character_key,
            )

            if not updated:
                raise ValueError(
                    f"NFT {token_id} not on character "
                    f"{from_character_key} of {from_wallet}"
                )

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=from_wallet,
                to_wallet=to_wallet,
                transfer_type=transfer_type,
            )

    # ================================================================== #
    #  6. CHARACTER <-> RESERVE (crafting)
    # ================================================================== #

    @staticmethod
    def craft_input(token_id, vault_address):
        with transaction.atomic():
            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_CHARACTER:
                raise ValueError(
                    f"NFT {token_id} is not in CHARACTER state "
                    f"(current: {nft.location})"
                )

            old_owner = nft.owner_in_game
            nft.location = NFTGameState.LOCATION_RESERVE
            nft.owner_in_game = vault_address
            nft.character_key = None
            NFTService._reset_token_identity(nft)
            nft.save(update_fields=[
                "location", "owner_in_game", "character_key",
                "item_type", "metadata", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=old_owner,
                to_wallet=vault_address,
                transfer_type="craft_input",
            )

    @staticmethod
    def craft_output(token_id, wallet_address, character_key):
        with transaction.atomic():
            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_RESERVE:
                raise ValueError(
                    f"NFT {token_id} is not in RESERVE state "
                    f"(current: {nft.location})"
                )

            old_owner = nft.owner_in_game
            nft.location = NFTGameState.LOCATION_CHARACTER
            nft.owner_in_game = wallet_address
            nft.character_key = character_key
            nft.save(update_fields=[
                "location", "owner_in_game", "character_key", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=old_owner,
                to_wallet=wallet_address,
                transfer_type="craft_output",
            )

    # ================================================================== #
    #  7. CHARACTER <-> AUCTION
    # ================================================================== #

    @staticmethod
    def list_auction(token_id):
        with transaction.atomic():
            updated = NFTGameState.objects.filter(
                nftoken_id=str(token_id),
                location=NFTGameState.LOCATION_CHARACTER,
            ).update(
                location=NFTGameState.LOCATION_AUCTION,
                character_key=None,
            )

            if not updated:
                raise ValueError(f"NFT {token_id} is not in CHARACTER state")

    @staticmethod
    def cancel_auction(token_id, character_key):
        with transaction.atomic():
            updated = NFTGameState.objects.filter(
                nftoken_id=str(token_id),
                location=NFTGameState.LOCATION_AUCTION,
            ).update(
                location=NFTGameState.LOCATION_CHARACTER,
                character_key=character_key,
            )

            if not updated:
                raise ValueError(f"NFT {token_id} is not in AUCTION state")

    @staticmethod
    def complete_auction(token_id, winner_wallet, character_key):
        with transaction.atomic():
            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_AUCTION:
                raise ValueError(
                    f"NFT {token_id} is not in AUCTION state "
                    f"(current: {nft.location})"
                )

            old_owner = nft.owner_in_game
            nft.location = NFTGameState.LOCATION_CHARACTER
            nft.owner_in_game = winner_wallet
            nft.character_key = character_key
            nft.save(update_fields=[
                "location", "owner_in_game", "character_key", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=old_owner,
                to_wallet=winner_wallet,
                transfer_type="auction_complete",
            )

    # ================================================================== #
    #  8. RESERVE <-> ACCOUNT
    # ================================================================== #

    @staticmethod
    def reserve_to_account(token_id, wallet_address, vault_address):
        with transaction.atomic():
            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_RESERVE:
                raise ValueError(
                    f"NFT {token_id} is not in RESERVE state "
                    f"(current: {nft.location})"
                )

            nft.location = NFTGameState.LOCATION_ACCOUNT
            nft.owner_in_game = wallet_address
            nft.save(update_fields=[
                "location", "owner_in_game", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=vault_address,
                to_wallet=wallet_address,
                transfer_type="reserve_to_account",
            )

    @staticmethod
    def account_to_reserve(token_id, vault_address):
        with transaction.atomic():
            nft = NFTGameState.objects.select_for_update().get(
                nftoken_id=str(token_id),
            )
            if nft.location != NFTGameState.LOCATION_ACCOUNT:
                raise ValueError(
                    f"NFT {token_id} is not in ACCOUNT state "
                    f"(current: {nft.location})"
                )

            old_owner = nft.owner_in_game
            nft.location = NFTGameState.LOCATION_RESERVE
            nft.owner_in_game = vault_address
            NFTService._reset_token_identity(nft)
            nft.save(update_fields=[
                "location", "owner_in_game",
                "item_type", "metadata", "updated_at",
            ])

            NFTTransferLog.objects.create(
                nftoken_id=str(token_id),
                from_wallet=old_owner,
                to_wallet=vault_address,
                transfer_type="account_to_reserve",
            )
