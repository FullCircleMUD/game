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

# Polygon compat params (ignored by XRPL services)
CHAIN_ID = 137
CONTRACT = "0xDEAD"
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
        nft = NFTService.get_nft(TOKEN_A, CHAIN_ID, CONTRACT)
        self.assertEqual(nft.nftoken_id, TOKEN_A)

    def test_get_character_nfts(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        _nft(TOKEN_B, "CHARACTER", PLAYER, CHAR_KEY)
        _nft(TOKEN_C, "ACCOUNT", PLAYER)
        qs = NFTService.get_character_nfts(PLAYER, CHAIN_ID, CONTRACT, CHAR_KEY)
        self.assertEqual(qs.count(), 2)

    def test_get_account_nfts(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        _nft(TOKEN_B, "CHARACTER", PLAYER, CHAR_KEY)
        qs = NFTService.get_account_nfts(PLAYER, CHAIN_ID, CONTRACT)
        self.assertEqual(qs.count(), 1)

    def test_get_available_for_spawn(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        _nft(TOKEN_B, "SPAWNED", VAULT)
        qs = NFTService.get_available_for_spawn(CHAIN_ID, CONTRACT, VAULT)
        self.assertEqual(qs.count(), 1)


class TestNFTServiceSpawnDespawn(TestCase):
    databases = {"default", "xrpl"}

    def test_spawn(self):
        _nft(TOKEN_A)
        NFTService.spawn(TOKEN_A, CHAIN_ID, CONTRACT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "SPAWNED")

    def test_spawn_not_in_reserve_raises(self):
        _nft(TOKEN_A, "SPAWNED")
        with self.assertRaises(ValueError):
            NFTService.spawn(TOKEN_A, CHAIN_ID, CONTRACT)

    def test_despawn(self):
        _nft(TOKEN_A, "SPAWNED")
        NFTService.despawn(TOKEN_A, CHAIN_ID, CONTRACT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "RESERVE")
        self.assertIsNone(nft.item_type)

    def test_despawn_not_in_spawned_raises(self):
        _nft(TOKEN_A, "RESERVE")
        with self.assertRaises(ValueError):
            NFTService.despawn(TOKEN_A, CHAIN_ID, CONTRACT)


class TestNFTServicePickupDrop(TestCase):
    databases = {"default", "xrpl"}

    def test_pickup(self):
        _nft(TOKEN_A, "SPAWNED", VAULT)
        NFTService.pickup(TOKEN_A, PLAYER, CHAIN_ID, CONTRACT, CHAR_KEY)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "CHARACTER")
        self.assertEqual(nft.owner_in_game, PLAYER)
        self.assertEqual(nft.character_key, CHAR_KEY)
        self.assertEqual(NFTTransferLog.objects.count(), 1)

    def test_pickup_not_spawned_raises(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        with self.assertRaises(ValueError):
            NFTService.pickup(TOKEN_A, PLAYER, CHAIN_ID, CONTRACT, CHAR_KEY)

    def test_drop(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.drop(TOKEN_A, CHAIN_ID, CONTRACT, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "SPAWNED")
        self.assertEqual(nft.owner_in_game, VAULT)
        self.assertIsNone(nft.character_key)

    def test_drop_not_on_character_raises(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        with self.assertRaises(ValueError):
            NFTService.drop(TOKEN_A, CHAIN_ID, CONTRACT, VAULT)


class TestNFTServiceBankUnbank(TestCase):
    databases = {"default", "xrpl"}

    def test_bank(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.bank(TOKEN_A, CHAIN_ID, CONTRACT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "ACCOUNT")
        self.assertIsNone(nft.character_key)

    def test_unbank(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.unbank(TOKEN_A, CHAIN_ID, CONTRACT, CHAR_KEY)
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
            CHAIN_ID, CONTRACT,
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
                CHAIN_ID, CONTRACT,
            )


class TestNFTServiceCrafting(TestCase):
    databases = {"default", "xrpl"}

    def test_craft_input(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.craft_input(TOKEN_A, CHAIN_ID, CONTRACT, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "RESERVE")
        self.assertEqual(nft.owner_in_game, VAULT)
        self.assertIsNone(nft.item_type)
        self.assertEqual(nft.metadata, {})

    def test_craft_output(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        NFTService.craft_output(TOKEN_A, PLAYER, CHAIN_ID, CONTRACT, CHAR_KEY)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "CHARACTER")
        self.assertEqual(nft.owner_in_game, PLAYER)
        self.assertEqual(nft.character_key, CHAR_KEY)


class TestNFTServiceAuction(TestCase):
    databases = {"default", "xrpl"}

    def test_list_and_cancel_auction(self):
        _nft(TOKEN_A, "CHARACTER", PLAYER, CHAR_KEY)
        NFTService.list_auction(TOKEN_A, CHAIN_ID, CONTRACT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "AUCTION")
        self.assertIsNone(nft.character_key)

        NFTService.cancel_auction(TOKEN_A, CHAIN_ID, CONTRACT, CHAR_KEY)
        nft.refresh_from_db()
        self.assertEqual(nft.location, "CHARACTER")

    def test_complete_auction(self):
        _nft(TOKEN_A, "AUCTION", PLAYER)
        NFTService.complete_auction(
            TOKEN_A, PLAYER2, CHAIN_ID, CONTRACT, CHAR_KEY2,
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

        result_id = NFTService.assign_item_type("Test Sword", CHAIN_ID, CONTRACT)
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
            NFTService.assign_item_type("Test Sword", CHAIN_ID, CONTRACT)


class TestNFTServiceReserveAccount(TestCase):
    databases = {"default", "xrpl"}

    def test_reserve_to_account(self):
        _nft(TOKEN_A, "RESERVE", VAULT)
        NFTService.reserve_to_account(TOKEN_A, PLAYER, CHAIN_ID, CONTRACT, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "ACCOUNT")
        self.assertEqual(nft.owner_in_game, PLAYER)

    def test_account_to_reserve(self):
        _nft(TOKEN_A, "ACCOUNT", PLAYER)
        NFTService.account_to_reserve(TOKEN_A, CHAIN_ID, CONTRACT, VAULT)
        nft = NFTGameState.objects.get(nftoken_id=TOKEN_A)
        self.assertEqual(nft.location, "RESERVE")
        self.assertEqual(nft.owner_in_game, VAULT)
        self.assertIsNone(nft.item_type)
