"""
Tests for BaseNFTItem — at_post_move dispatch and at_object_delete dispatch.

Uses EvenniaTest for real Evennia objects (characters, rooms) and mocks
the NFTService calls since those are already tested in blockchain_tests.
We're testing that the HOOKS call the RIGHT SERVICE METHODS with the
RIGHT ARGUMENTS based on source/destination classification.
"""

from unittest.mock import patch, MagicMock

from django.conf import settings

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


# ── Constants ────────────────────────────────────────────────────────────

VAULT = settings.XRPL_VAULT_ADDRESS
TOKEN_ID = 42
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"


class TestBaseNFTItemPostMove(EvenniaTest):
    """
    Test that at_post_move dispatches to the correct NFTService method
    based on the source and destination location types.
    """

    # Override room typeclass to use RoomBase (has FungibleInventoryMixin)
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Set up wallet addresses on accounts so _get_owner_wallet works
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)

        # Create an AccountBank for char1's account
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-TestAccount",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A

    def _make_nft(self, location=None):
        """
        Create a BaseNFTItem with NFT attributes set, optionally at a location.

        NOTE: create_object's attributes kwarg doesn't reliably overwrite
        AttributeProperty defaults before at_post_move fires, so we create
        without location, set attributes directly, then move_to.
        """
        nft = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Test Sword",
            nohome=True,
        )
        nft.token_id = TOKEN_ID
        if location:
            nft.move_to(location)
        return nft

    def _make_nft_raw(self, location):
        """
        Place an NFT at a location WITHOUT triggering at_post_move.
        Used to set up initial state for movement tests.
        """
        nft = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Test Sword",
            nohome=True,
        )
        nft.token_id = TOKEN_ID
        nft.db_location = location
        nft.save(update_fields=["db_location"])
        return nft

    # ── Creation tests (source_location is None) ──────────────────────
    # These test the at_post_move(source_location=None) path which fires
    # when an NFT is first placed into the world via move_to from no location.

    @patch("blockchain.xrpl.services.nft.NFTService.spawn")
    def test_create_into_room_calls_spawn(self, mock_spawn):
        """Creating an NFT into a room should call NFTService.spawn."""
        self._make_nft(location=self.room1)
        mock_spawn.assert_called_once_with(TOKEN_ID)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_output")
    def test_create_into_character_calls_craft_output(self, mock_craft):
        """Creating an NFT into a character should call NFTService.craft_output."""
        self._make_nft(location=self.char1)
        mock_craft.assert_called_once_with(
            TOKEN_ID, WALLET_A, self.char1.key,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.craft_output")
    def test_create_into_char2_uses_correct_wallet(self, mock_craft):
        """Creating into char2 should use wallet B and char2's key."""
        self._make_nft(location=self.char2)
        mock_craft.assert_called_once_with(
            TOKEN_ID, WALLET_B, self.char2.key,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.deposit_from_chain")
    def test_create_into_account_bank_calls_deposit_from_chain(self, mock_deposit):
        """Creating an NFT into an AccountBank = deposit_from_chain (ONCHAIN → ACCOUNT)."""
        self._make_nft(location=self.bank)
        mock_deposit.assert_called_once_with(
            TOKEN_ID, WALLET_A,
            settings.XRPL_VAULT_ADDRESS, None,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.deposit_from_chain")
    def test_create_into_account_bank_with_tx_hash(self, mock_deposit):
        """Creating into AccountBank via move_to with tx_hash passes it through."""
        nft = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Test Sword",
            nohome=True,
        )
        nft.token_id = TOKEN_ID
        nft.move_to(self.bank, tx_hash="0xdeadbeef")
        mock_deposit.assert_called_once_with(
            TOKEN_ID, WALLET_A,
            settings.XRPL_VAULT_ADDRESS, "0xdeadbeef",
        )

    # ── Movement tests (source_location is not None) ──────────────────

    @patch("blockchain.xrpl.services.nft.NFTService.pickup")
    def test_room_to_character_calls_pickup(self, mock_pickup):
        """Moving an NFT from a room to a character = pickup."""
        nft = self._make_nft_raw(self.room1)
        nft.move_to(self.char1)
        mock_pickup.assert_called_once_with(
            TOKEN_ID, WALLET_A, self.char1.key,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.drop")
    def test_character_to_room_calls_drop(self, mock_drop):
        """Moving an NFT from a character to a room = drop."""
        nft = self._make_nft_raw(self.char1)
        nft.move_to(self.room1)
        mock_drop.assert_called_once_with(
            TOKEN_ID, VAULT,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.transfer")
    def test_character_to_character_calls_transfer(self, mock_transfer):
        """Moving an NFT between characters = transfer."""
        nft = self._make_nft_raw(self.char1)
        nft.move_to(self.char2)
        mock_transfer.assert_called_once_with(
            TOKEN_ID, WALLET_A, self.char1.key,
            WALLET_B, self.char2.key,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_character_to_bank_calls_bank(self, mock_bank):
        """Moving an NFT from a character to an AccountBank = bank."""
        nft = self._make_nft_raw(self.char1)
        nft.move_to(self.bank)
        mock_bank.assert_called_once_with(
            TOKEN_ID,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.unbank")
    def test_bank_to_character_calls_unbank(self, mock_unbank):
        """Moving an NFT from an AccountBank to a character = unbank."""
        nft = self._make_nft_raw(self.bank)
        nft.move_to(self.char1)
        mock_unbank.assert_called_once_with(
            TOKEN_ID, self.char1.key,
        )

    def test_room_to_room_no_service_call(self):
        """Moving an NFT between rooms should not call any service method."""
        nft = self._make_nft_raw(self.room1)
        with patch("blockchain.xrpl.services.nft.NFTService.pickup") as mock_pickup, \
             patch("blockchain.xrpl.services.nft.NFTService.drop") as mock_drop:
            nft.move_to(self.room2)
            mock_pickup.assert_not_called()
            mock_drop.assert_not_called()

    def test_no_service_call_without_token_id(self):
        """Items without token_id should not trigger any service calls."""
        nft = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Uninitialized",
            nohome=True,
        )
        nft.db_location = self.room1
        nft.save(update_fields=["db_location"])
        # token_id is None — at_post_move should return early
        with patch("blockchain.xrpl.services.nft.NFTService.pickup") as mock_pickup:
            nft.move_to(self.char1)
            mock_pickup.assert_not_called()


class TestBaseNFTItemDelete(EvenniaTest):
    """
    Test that at_object_delete dispatches to the correct NFTService method
    based on where the item currently is when deleted.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-TestAccount",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A

    def _place_nft(self, location):
        """Create an NFT and place it at a location without triggering hooks."""
        nft = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Test Sword",
            nohome=True,
        )
        nft.token_id = TOKEN_ID
        nft.db_location = location
        nft.save(update_fields=["db_location"])
        return nft

    @patch("blockchain.xrpl.services.nft.NFTService.despawn")
    def test_delete_from_room_calls_despawn(self, mock_despawn):
        """Deleting an NFT from a room = despawn (SPAWNED → RESERVE)."""
        nft = self._place_nft(self.room1)
        nft.delete()
        mock_despawn.assert_called_once_with(TOKEN_ID)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_delete_from_character_calls_craft_input(self, mock_craft):
        """Deleting an NFT from a character = craft_input (CHARACTER → RESERVE)."""
        nft = self._place_nft(self.char1)
        nft.delete()
        mock_craft.assert_called_once_with(
            TOKEN_ID, VAULT,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.withdraw_to_chain")
    def test_delete_from_account_bank_calls_withdraw_to_chain(self, mock_withdraw):
        """Deleting an NFT from an AccountBank = withdraw_to_chain (ACCOUNT → ONCHAIN)."""
        nft = self._place_nft(self.bank)
        nft.ndb.pending_tx_hash = "0xdeadbeef"
        nft.delete()
        mock_withdraw.assert_called_once_with(
            TOKEN_ID, "0xdeadbeef",
        )

    @patch("blockchain.xrpl.services.nft.NFTService.withdraw_to_chain")
    def test_delete_from_account_bank_no_tx_hash(self, mock_withdraw):
        """Deleting without a tx_hash stashed passes None."""
        nft = self._place_nft(self.bank)
        nft.delete()
        mock_withdraw.assert_called_once_with(
            TOKEN_ID, None,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.despawn")
    def test_delete_without_token_id_no_service_call(self, mock_despawn):
        """Deleting an item without token_id should not call any service."""
        nft = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Uninitialized",
            location=self.room1,
        )
        nft.delete()
        mock_despawn.assert_not_called()


class TestGetOwnerWallet(EvenniaTest):
    """Test the _get_owner_wallet staticmethod on NFTMirrorMixin."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_returns_wallet_for_character_with_account(self):
        from typeclasses.mixins.nft_mirror import NFTMirrorMixin
        self.assertEqual(
            NFTMirrorMixin._get_owner_wallet(self.char1), WALLET_A,
        )

    def test_returns_none_for_character_without_wallet(self):
        from typeclasses.mixins.nft_mirror import NFTMirrorMixin
        self.account.attributes.remove("wallet_address")
        self.assertIsNone(NFTMirrorMixin._get_owner_wallet(self.char1))

    def test_returns_none_for_none(self):
        from typeclasses.mixins.nft_mirror import NFTMirrorMixin
        self.assertIsNone(NFTMirrorMixin._get_owner_wallet(None))

    def test_returns_none_for_character_without_account(self):
        """An NPC-like object with no account should return None."""
        from typeclasses.mixins.nft_mirror import NFTMirrorMixin
        from evennia.utils import create
        npc = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="NPC",
            nohome=True,
        )
        npc.account = None
        self.assertIsNone(NFTMirrorMixin._get_owner_wallet(npc))
        npc.delete()


class TestContainerNFTItemPostMove(EvenniaTest):
    """
    Test that ContainerNFTItem (which mixes FungibleInventoryMixin and
    NFTMirrorMixin) correctly dispatches mirror transitions.

    Regression test: FungibleInventoryMixin._get_wallet (no-arg instance
    method) previously shadowed NFTMirrorMixin._get_wallet (staticmethod
    taking a character arg) due to MRO, causing a TypeError on pickup.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)

    def _make_container_raw(self, location):
        """Place a ContainerNFTItem at location without triggering hooks."""
        from evennia.utils import create
        container = create.create_object(
            "typeclasses.items.containers.container_nft_item.ContainerNFTItem",
            key="Backpack",
            nohome=True,
        )
        container.token_id = TOKEN_ID
        container.db_location = location
        container.save(update_fields=["db_location"])
        return container

    @patch("blockchain.xrpl.services.nft.NFTService.pickup")
    def test_container_room_to_character_calls_pickup(self, mock_pickup):
        """Picking up a container should call NFTService.pickup without TypeError."""
        container = self._make_container_raw(self.room1)
        result = container.move_to(self.char1, move_type="get")
        self.assertTrue(result)
        mock_pickup.assert_called_once_with(
            TOKEN_ID, WALLET_A, self.char1.key,
        )

    @patch("blockchain.xrpl.services.nft.NFTService.drop")
    def test_container_character_to_room_calls_drop(self, mock_drop):
        """Dropping a container should call NFTService.drop."""
        container = self._make_container_raw(self.char1)
        result = container.move_to(self.room1, move_type="drop")
        self.assertTrue(result)
        mock_drop.assert_called_once_with(TOKEN_ID, VAULT)

    @patch("blockchain.xrpl.services.nft.NFTService.transfer")
    def test_container_character_to_character_calls_transfer(self, mock_transfer):
        """Giving a container between characters should call NFTService.transfer."""
        container = self._make_container_raw(self.char1)
        result = container.move_to(self.char2, move_type="give")
        self.assertTrue(result)
        mock_transfer.assert_called_once_with(
            TOKEN_ID, WALLET_A, self.char1.key,
            WALLET_B, self.char2.key,
        )


class TestBaseNFTItemClassify(EvenniaTest):
    """Test the _classify helper returns correct types."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-TestAccount",
            nohome=True,
        )

    def test_classify_character(self):
        from typeclasses.items.base_nft_item import BaseNFTItem
        self.assertEqual(BaseNFTItem._classify(self.char1), "CHARACTER")

    def test_classify_account_bank(self):
        from typeclasses.items.base_nft_item import BaseNFTItem
        self.assertEqual(BaseNFTItem._classify(self.bank), "ACCOUNT")

    def test_classify_room(self):
        from typeclasses.items.base_nft_item import BaseNFTItem
        self.assertEqual(BaseNFTItem._classify(self.room1), "WORLD")

    def test_classify_none(self):
        from typeclasses.items.base_nft_item import BaseNFTItem
        self.assertIsNone(BaseNFTItem._classify(None))


class TestBaseNFTItemGetNFTMirror(EvenniaTest):
    """Test the get_nft_mirror static method delegates to NFTService."""

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.nft.NFTService.get_nft")
    def test_get_nft_mirror_delegates_to_service(self, mock_get):
        """get_nft_mirror should forward args to NFTService.get_nft."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        mock_get.return_value = MagicMock()
        result = BaseNFTItem.get_nft_mirror(TOKEN_ID)
        mock_get.assert_called_once_with(TOKEN_ID)
        self.assertEqual(result, mock_get.return_value)


class TestBaseNFTItemAssignToBlankToken(EvenniaTest):
    """Test assign_to_blank_token delegates to NFTService.assign_item_type."""

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.nft.NFTService.assign_item_type")
    def test_delegates_to_service_with_settings(self, mock_assign):
        """assign_to_blank_token passes settings values to NFTService."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        mock_assign.return_value = 7
        result = BaseNFTItem.assign_to_blank_token("Iron Longsword")
        mock_assign.assert_called_once_with("Iron Longsword")
        self.assertEqual(result, 7)

    @patch("blockchain.xrpl.services.nft.NFTService.assign_item_type")
    def test_propagates_does_not_exist(self, mock_assign):
        """Unknown item type name should propagate DoesNotExist."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        from blockchain.xrpl.models import NFTItemType
        mock_assign.side_effect = NFTItemType.DoesNotExist
        with self.assertRaises(NFTItemType.DoesNotExist):
            BaseNFTItem.assign_to_blank_token("Nonexistent")

    @patch("blockchain.xrpl.services.nft.NFTService.assign_item_type")
    def test_propagates_value_error(self, mock_assign):
        """No blanks available should propagate ValueError."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        mock_assign.side_effect = ValueError("No blank tokens")
        with self.assertRaises(ValueError):
            BaseNFTItem.assign_to_blank_token("Iron Longsword")


class TestBaseNFTItemSpawnInto(EvenniaTest):
    """Test spawn_into creates an Evennia object and moves it to location."""

    databases = {"default", "xrpl"}
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from blockchain.xrpl.models import NFTGameState, NFTItemType
        self.item_type = NFTItemType.objects.create(
            name="Spawn Test Blade",
            typeclass="typeclasses.items.base_nft_item.BaseNFTItem",
            prototype_key="",
            description="A test blade.",
            default_metadata={"durability": 80},
        )
        self.nft_row = NFTGameState.objects.create(
            nftoken_id="10100",
            taxon=0,
            owner_in_game=settings.XRPL_VAULT_ADDRESS,
            location="RESERVE",
            item_type=self.item_type,
            metadata={"durability": 80},
        )

    def tearDown(self):
        from blockchain.xrpl.models import NFTGameState, NFTItemType
        NFTGameState.objects.filter(nftoken_id="10100").delete()
        self.item_type.delete()
        super().tearDown()

    @patch("blockchain.xrpl.services.nft.NFTService.spawn")
    def test_spawn_into_creates_object_at_location(self, mock_spawn):
        """spawn_into should create an object and move it to the location."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        obj = BaseNFTItem.spawn_into(10100, self.room1)
        self.assertIsNotNone(obj)
        self.assertEqual(obj.location, self.room1)

    @patch("blockchain.xrpl.services.nft.NFTService.spawn")
    def test_spawn_into_sets_nft_attributes(self, mock_spawn):
        """spawn_into should set token_id."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        obj = BaseNFTItem.spawn_into(10100, self.room1)
        self.assertEqual(obj.token_id, 10100)

    @patch("blockchain.xrpl.services.nft.NFTService.spawn")
    def test_spawn_into_applies_metadata(self, mock_spawn):
        """spawn_into should apply metadata as Evennia attributes."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        obj = BaseNFTItem.spawn_into(10100, self.room1)
        self.assertEqual(obj.attributes.get("durability"), 80)

    @patch("blockchain.xrpl.services.nft.NFTService.spawn")
    def test_spawn_into_sets_key_from_item_type(self, mock_spawn):
        """spawn_into should set object key from item_type.name."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        obj = BaseNFTItem.spawn_into(10100, self.room1)
        self.assertEqual(obj.key, "Spawn Test Blade")

    @patch("blockchain.xrpl.services.nft.NFTService.spawn")
    def test_spawn_into_calls_spawn_service(self, mock_spawn):
        """spawn_into move_to should trigger NFTService.spawn."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        BaseNFTItem.spawn_into(10100, self.room1)
        mock_spawn.assert_called_once_with(10100)

    def test_spawn_into_returns_none_for_missing_token(self):
        """spawn_into should return None if NFTMirror row doesn't exist."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        result = BaseNFTItem.spawn_into(9999, self.room1)
        self.assertIsNone(result)

    @patch("blockchain.xrpl.services.nft.NFTService.spawn")
    def test_spawn_into_blank_token_uses_fallback_key(self, mock_spawn):
        """spawn_into for a token with no item_type should use 'NFT #N' as key."""
        from typeclasses.items.base_nft_item import BaseNFTItem
        from blockchain.xrpl.models import NFTGameState
        # Create a blank token (no item_type)
        NFTGameState.objects.create(
            nftoken_id="10101",
            taxon=0,
            owner_in_game=settings.XRPL_VAULT_ADDRESS,
            location="RESERVE",
            item_type=None,
            metadata={},
        )
        obj = BaseNFTItem.spawn_into(10101, self.room1)
        self.assertEqual(obj.key, "NFT #10101")
        # Cleanup
        NFTGameState.objects.filter(nftoken_id="10101").delete()
