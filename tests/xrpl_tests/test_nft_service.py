"""
Tests for XRPL NFTService.

Uses real database rows (no mocks). Django TestCase auto-rolls
back after each test.
"""

from django.test import TestCase

from blockchain.xrpl.models import (
    NFTGameState,
    NFTItemType,
    NFTTransferLog,
    XRPLTransactionLog,
)
from blockchain.xrpl.services.nft import NFTService


# Test constants
ISSUER = "rISSUER_ADDRESS_TEST"
PLAYER = "rPLAYER_ADDRESS_TEST"
PLAYER2 = "rPLAYER2_ADDRESS_TEST"
CHAR_KEY = "char#1234"
CHAR_KEY2 = "char#5678"

VAULT = ISSUER

# Use high nftoken_ids to avoid seed data collisions
TOKEN_A = "000A" + "0" * 60
TOKEN_B = "000B" + "0" * 60
TOKEN_C = "000C" + "0" * 60


def _nft(nftoken_id, location="RESERVE", owner=ISSUER, character_key=None,
         item_type=None):
    """Create an NFTGameState row for testing."""
    return NFTGameState.objects.create(
        nftoken_id=nftoken_id,
        taxon=1,
        owner_in_game=owner,
        location=location,
        character_key=character_key,
        item_type=item_type,
        metadata={},
    )


class TestNFTServiceQueries(TestCase):
    databases = {"default", "xrpl"}

    def test_get_nft(self):
        _nft(TOKEN_A)
        nft = NFTService.get_nft(TOKEN_A)
        self.assertEqual(nft.nftoken_id, TOKEN_A)

    def test_get_character_nfts(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        _nft(TOKEN_B, "CHARACTER", PLAYER, CHAR_KEY)
        _nft(TOKEN_C, "ACCOUNT", PLAYER)
        qs = NFTService.get_character_nfts(PLAYER, CHAR_KEY)
        self.assertEqual(qs.count(), 2)

    def test_get_account_nfts(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        _nft(TOKEN_B, "CHARACTER", PLAYER, CHAR_KEY)
        qs = NFTService.get_account_nfts(PLAYER)
        self.assertEqual(qs.count(), 1)

    def test_get_available_for_spawn(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        _nft(TOKEN_B, "SPAWNED", VAULT)
        qs = NFTService.get_available_for_spawn(VAULT)
        self.assertEqual(qs.count(), 1)


class TestNFTServiceSpawnDespawn(TestCase):
    databases = {"default", "xrpl"}

    def test_spawn(self):
        _nft(TOKEN_A)
        NFTService.spawn(TOKEN_A)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "SPAWNED")

    def test_spawn_not_in_reserve_raises(self):
        _nft(TOKEN_A, "SPAWNED")
        with self.assertRaises(ValueError):
            NFTService.spawn(TOKEN_A)

    def test_despawn(self):
        _nft(TOKEN_A, "SPAWNED")
        NFTService.despawn(TOKEN_A)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "RESERVE")
        self.assertIsNone(nft.item_type)

    def test_despawn_not_in_spawned_raises(self):
        _nft(TOKEN_A, "RESERVE")
        with self.assertRaises(ValueError):
            NFTService.despawn(TOKEN_A)


class TestNFTServiceUpdateMetadata(TestCase):
    databases = {"default", "xrpl"}

    def test_merges_into_existing_metadata(self):
        nft = _nft(TOKEN_A)
        nft.metadata = {"keep_me": "present", "overwrite_me": 1}
        nft.save(update_fields=["metadata"])

        NFTService.update_metadata(TOKEN_A, {"overwrite_me": 2, "new_key": "x"})

        nft.refresh_from_db()
        self.assertEqual(nft.metadata["keep_me"], "present")
        self.assertEqual(nft.metadata["overwrite_me"], 2)
        self.assertEqual(nft.metadata["new_key"], "x")

    def test_none_value_deletes_key(self):
        nft = _nft(TOKEN_A)
        nft.metadata = {"doomed": "bye", "surviving": "hi"}
        nft.save(update_fields=["metadata"])

        NFTService.update_metadata(TOKEN_A, {"doomed": None})

        nft.refresh_from_db()
        self.assertNotIn("doomed", nft.metadata)
        self.assertEqual(nft.metadata["surviving"], "hi")

    def test_none_delete_on_missing_key_is_noop(self):
        _nft(TOKEN_A)
        # Should not raise even though "never_existed" isn't in metadata
        NFTService.update_metadata(TOKEN_A, {"never_existed": None})
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.metadata, {})

    def test_missing_token_raises(self):
        with self.assertRaises(NFTGameState.DoesNotExist):
            NFTService.update_metadata("NONEXISTENT" + "0" * 54, {"k": "v"})

    def test_empty_patch_is_noop(self):
        _nft(TOKEN_A)
        # Should not touch the DB at all — no DoesNotExist even on a row
        # that exists, because the early return fires before the query.
        NFTService.update_metadata(TOKEN_A, {})
        NFTService.update_metadata(TOKEN_A, None)

class TestNFTServicePickupDrop(TestCase):
    databases = {"default", "xrpl"}

    def test_pickup(self):
        _nft(TOKEN_A, "SPAWNED", VAULT)
        NFTService.pickup(TOKEN_A, PLAYER, CHAR_KEY)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "CHARACTER")
        self.assertEqual(nft.owner_in_game, PLAYER)
        self.assertEqual(nft.character_key, CHAR_KEY)
        self.assertEqual(NFTTransferLog.objects.count(), 1)

    def test_pickup_not_spawned_raises(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        with self.assertRaises(ValueError):
            NFTService.pickup(TOKEN_A, PLAYER, CHAR_KEY)

    def test_drop(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.drop(TOKEN_A, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "SPAWNED")
        self.assertEqual(nft.owner_in_game, VAULT)
        self.assertIsNone(nft.character_key)

    def test_drop_not_on_character_raises(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        with self.assertRaises(ValueError):
            NFTService.drop(TOKEN_A, VAULT)


class TestNFTServiceBankUnbank(TestCase):
    databases = {"default", "xrpl"}

    def test_bank(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.bank(TOKEN_A)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "ACCOUNT")
        self.assertIsNone(nft.character_key)

    def test_unbank(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.unbank(TOKEN_A, CHAR_KEY)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "CHARACTER")
        self.assertEqual(nft.character_key, CHAR_KEY)


class TestNFTServiceChainOperations(TestCase):
    databases = {"default", "xrpl"}

    def test_deposit_from_chain(self):
        _nft(TOKEN_A, "ONCHAIN", owner=None)
        NFTService.deposit_from_chain(
            TOKEN_A, PLAYER, VAULT, "TX123",
        )
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "ACCOUNT")
        self.assertEqual(nft.owner_in_game, PLAYER)
        self.assertEqual(XRPLTransactionLog.objects.count(), 1)

    def test_deposit_from_chain_duplicate_tx_rejected(self):
        """Same tx_hash should not import the NFT twice."""
        _nft(TOKEN_A, "ONCHAIN", owner=None)
        NFTService.deposit_from_chain(TOKEN_A, PLAYER, VAULT, "TX_DUPE")
        # Try again with same tx_hash
        with self.assertRaises(ValueError) as ctx:
            NFTService.deposit_from_chain(TOKEN_A, PLAYER, VAULT, "TX_DUPE")
        self.assertIn("already processed", str(ctx.exception))

    def test_withdraw_to_chain(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.withdraw_to_chain(TOKEN_A, "TX456")
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "ONCHAIN")
        self.assertIsNone(nft.owner_in_game)
        self.assertEqual(XRPLTransactionLog.objects.count(), 1)

    def test_withdraw_to_chain_duplicate_tx_rejected(self):
        """Same tx_hash should not export the NFT twice."""
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.withdraw_to_chain(TOKEN_A, "TX_DUPE")
        with self.assertRaises(ValueError) as ctx:
            NFTService.withdraw_to_chain(TOKEN_A, "TX_DUPE")
        self.assertIn("already processed", str(ctx.exception))


class TestNFTServiceTransfer(TestCase):
    databases = {"default", "xrpl"}

    def test_transfer(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.transfer(
            TOKEN_A, PLAYER, CHAR_KEY, PLAYER2, CHAR_KEY2,
        )
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.owner_in_game, PLAYER2)
        self.assertEqual(nft.character_key, CHAR_KEY2)
        self.assertEqual(NFTTransferLog.objects.count(), 1)

    def test_transfer_wrong_owner_raises(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        with self.assertRaises(ValueError):
            NFTService.transfer(
                TOKEN_A, PLAYER2, CHAR_KEY2, PLAYER, CHAR_KEY,
            )


class TestNFTServiceCrafting(TestCase):
    databases = {"default", "xrpl"}

    def test_craft_input(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.craft_input(TOKEN_A, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "RESERVE")
        self.assertEqual(nft.owner_in_game, VAULT)
        self.assertIsNone(nft.item_type)
        self.assertEqual(nft.metadata, {})

    def test_craft_output(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        NFTService.craft_output(TOKEN_A, PLAYER, CHAR_KEY)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "CHARACTER")
        self.assertEqual(nft.owner_in_game, PLAYER)
        self.assertEqual(nft.character_key, CHAR_KEY)


class TestNFTServiceAuction(TestCase):
    databases = {"default", "xrpl"}

    def test_list_and_cancel_auction(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.list_auction(TOKEN_A)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "AUCTION")
        self.assertIsNone(nft.character_key)

        NFTService.cancel_auction(TOKEN_A, CHAR_KEY)
        nft.refresh_from_db()
        self.assertEqual(nft.location, "CHARACTER")

    def test_complete_auction(self):
        _nft(TOKEN_A, "AUCTION", PLAYER)
        NFTService.complete_auction(
            TOKEN_A, PLAYER2, CHAR_KEY2,
        )
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.owner_in_game, PLAYER2)
        self.assertEqual(nft.character_key, CHAR_KEY2)
        self.assertEqual(NFTTransferLog.objects.count(), 1)


class TestNFTServiceAssignItemType(TestCase):
    databases = {"default", "xrpl"}

    def test_assign_item_type(self):
        # Create item type and blank token
        it = NFTItemType.objects.create(
            name="Test Sword",
            typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
            default_metadata={"durability": 100},
        )
        _nft(TOKEN_A, "RESERVE", VAULT)
        _nft(TOKEN_B, "RESERVE", VAULT)

        result_id = NFTService.assign_item_type("Test Sword")
        self.assertEqual(result_id, TOKEN_A)  # lowest nftoken_id
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.item_type, it)
        self.assertEqual(nft.metadata, {"durability": 100})

    def test_assign_item_type_no_blanks_raises(self):
        NFTItemType.objects.create(
            name="Test Sword",
            typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
        )
        # Clear any seed blank tokens so the pool is empty
        NFTGameState.objects.filter(
            location="RESERVE", item_type__isnull=True,
        ).delete()
        with self.assertRaises(ValueError):
            NFTService.assign_item_type("Test Sword")


class TestNFTServiceReserveAccount(TestCase):
    databases = {"default", "xrpl"}

    def test_reserve_to_account(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        NFTService.reserve_to_account(TOKEN_A, PLAYER, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "ACCOUNT")
        self.assertEqual(nft.owner_in_game, PLAYER)

    def test_reserve_to_account_not_in_reserve_raises(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        with self.assertRaises(ValueError):
            NFTService.reserve_to_account(TOKEN_A, PLAYER, VAULT)

    def test_account_to_reserve(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.account_to_reserve(TOKEN_A, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "RESERVE")
        self.assertEqual(nft.owner_in_game, VAULT)
        self.assertIsNone(nft.item_type)

    def test_account_to_reserve_not_in_account_raises(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        with self.assertRaises(ValueError):
            NFTService.account_to_reserve(TOKEN_A, VAULT)


class TestNFTServiceWrongStateRejection(TestCase):
    """Test that every state-transition method rejects NFTs in the wrong state."""

    databases = {"default", "xrpl"}

    def test_bank_not_in_character_raises(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        with self.assertRaises(ValueError):
            NFTService.bank(TOKEN_A)

    def test_unbank_not_in_account_raises(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        with self.assertRaises(ValueError):
            NFTService.unbank(TOKEN_A, CHAR_KEY)

    def test_deposit_not_in_onchain_raises(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        with self.assertRaises(ValueError):
            NFTService.deposit_from_chain(TOKEN_A, PLAYER, VAULT, "TX_NEW")

    def test_withdraw_not_in_account_raises(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        with self.assertRaises(ValueError):
            NFTService.withdraw_to_chain(TOKEN_A, "TX_NEW")

    def test_craft_input_not_in_character_raises(self):
        _nft(TOKEN_A, "SPAWNED", VAULT)
        with self.assertRaises(ValueError):
            NFTService.craft_input(TOKEN_A, VAULT)

    def test_craft_output_not_in_reserve_raises(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        with self.assertRaises(ValueError):
            NFTService.craft_output(TOKEN_A, PLAYER, CHAR_KEY)

    def test_list_auction_not_in_character_raises(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        with self.assertRaises(ValueError):
            NFTService.list_auction(TOKEN_A)

    def test_cancel_auction_not_in_auction_raises(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        with self.assertRaises(ValueError):
            NFTService.cancel_auction(TOKEN_A, CHAR_KEY)

    def test_complete_auction_not_in_auction_raises(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        with self.assertRaises(ValueError):
            NFTService.complete_auction(TOKEN_A, PLAYER2, CHAR_KEY2)


class TestNFTServiceTransferLogContent(TestCase):
    """Verify NFTTransferLog fields are populated correctly."""

    databases = {"default", "xrpl"}

    def test_pickup_log_content(self):
        _nft(TOKEN_A, "SPAWNED", VAULT)
        NFTService.pickup(TOKEN_A, PLAYER, CHAR_KEY)
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.nftoken_id, TOKEN_A)
        self.assertEqual(log.from_wallet, VAULT)
        self.assertEqual(log.to_wallet, PLAYER)
        self.assertEqual(log.transfer_type, "pickup")

    def test_drop_log_content(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.drop(TOKEN_A, VAULT)
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, PLAYER)
        self.assertEqual(log.to_wallet, VAULT)
        self.assertEqual(log.transfer_type, "drop")

    def test_deposit_log_content(self):
        _nft(TOKEN_A, "ONCHAIN", owner=None)
        NFTService.deposit_from_chain(TOKEN_A, PLAYER, VAULT, "TX_LOG")
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, VAULT)
        self.assertEqual(log.to_wallet, PLAYER)
        self.assertEqual(log.transfer_type, "deposit_from_chain")

    def test_withdraw_log_content(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.withdraw_to_chain(TOKEN_A, "TX_LOG")
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, PLAYER)
        self.assertEqual(log.to_wallet, "ONCHAIN")
        self.assertEqual(log.transfer_type, "withdraw_to_chain")

    def test_craft_input_log_content(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.craft_input(TOKEN_A, VAULT)
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, PLAYER)
        self.assertEqual(log.to_wallet, VAULT)
        self.assertEqual(log.transfer_type, "craft_input")

    def test_craft_output_log_content(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        NFTService.craft_output(TOKEN_A, PLAYER, CHAR_KEY)
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, VAULT)
        self.assertEqual(log.to_wallet, PLAYER)
        self.assertEqual(log.transfer_type, "craft_output")

    def test_auction_complete_log_content(self):
        _nft(TOKEN_A, "AUCTION", PLAYER)
        NFTService.complete_auction(TOKEN_A, PLAYER2, CHAR_KEY2)
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, PLAYER)
        self.assertEqual(log.to_wallet, PLAYER2)
        self.assertEqual(log.transfer_type, "auction_complete")

    def test_reserve_to_account_log_content(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        NFTService.reserve_to_account(TOKEN_A, PLAYER, VAULT)
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, VAULT)
        self.assertEqual(log.to_wallet, PLAYER)
        self.assertEqual(log.transfer_type, "reserve_to_account")

    def test_account_to_reserve_log_content(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.account_to_reserve(TOKEN_A, VAULT)
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, PLAYER)
        self.assertEqual(log.to_wallet, VAULT)
        self.assertEqual(log.transfer_type, "account_to_reserve")

    def test_transfer_log_content(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.transfer(
            TOKEN_A, PLAYER, CHAR_KEY, PLAYER2, CHAR_KEY2,
        )
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.from_wallet, PLAYER)
        self.assertEqual(log.to_wallet, PLAYER2)
        self.assertEqual(log.transfer_type, "trade")

    def test_transfer_custom_type_log_content(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.transfer(
            TOKEN_A, PLAYER, CHAR_KEY, PLAYER2, CHAR_KEY2,
            transfer_type="give",
        )
        log = NFTTransferLog.objects.get()
        self.assertEqual(log.transfer_type, "give")


class TestNFTServiceAssignItemTypeEdgeCases(TestCase):
    """Edge cases for assign_item_type."""

    databases = {"default", "xrpl"}

    def test_assign_item_type_unknown_name_raises(self):
        """Nonexistent item type name should raise DoesNotExist."""
        with self.assertRaises(NFTItemType.DoesNotExist):
            NFTService.assign_item_type("Nonexistent Sword")

    def test_assign_picks_lowest_nftoken_id(self):
        """Should assign to the blank token with the lowest nftoken_id."""
        it = NFTItemType.objects.create(
            name="Order Test",
            typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
        )
        _nft(TOKEN_C)  # higher id
        _nft(TOKEN_A)  # lower id
        _nft(TOKEN_B)  # middle id

        result_id = NFTService.assign_item_type("Order Test")
        self.assertEqual(result_id, TOKEN_A)

    def test_assign_skips_tokens_with_existing_item_type(self):
        """Should only pick blank tokens (item_type=None)."""
        it = NFTItemType.objects.create(
            name="Skip Test",
            typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
        )
        _nft(TOKEN_A, item_type=it)  # already assigned
        _nft(TOKEN_B)  # blank

        result_id = NFTService.assign_item_type("Skip Test")
        self.assertEqual(result_id, TOKEN_B)

    def test_assign_copies_default_metadata(self):
        """Assigned token should get the item type's default_metadata."""
        it = NFTItemType.objects.create(
            name="Meta Test",
            typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
            default_metadata={"rarity": "rare", "bonus": 5},
        )
        _nft(TOKEN_A)
        NFTService.assign_item_type("Meta Test")
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.metadata, {"rarity": "rare", "bonus": 5})
