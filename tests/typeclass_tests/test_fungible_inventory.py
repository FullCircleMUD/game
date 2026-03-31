"""
Tests for FungibleInventoryMixin — service dispatch for gold and resource
transfers/receives, local state management, and classification helpers.

Uses EvenniaTest for real Evennia objects (characters, rooms) and mocks
the GoldService/ResourceService calls since those are already tested in
blockchain_tests. We're testing that the MIXIN calls the RIGHT SERVICE
METHODS with the RIGHT ARGUMENTS based on source/target classification,
and that local state is updated correctly on both sides.
"""

from unittest.mock import patch, MagicMock

from django.conf import settings

from evennia.utils.test_resources import EvenniaTest
from evennia.utils import create


# ── Constants ────────────────────────────────────────────────────────────

VAULT = settings.XRPL_VAULT_ADDRESS
CHAIN_ID = settings.BLOCKCHAIN_CHAIN_ID
GOLD_CONTRACT = settings.CONTRACT_GOLD
RESOURCE_CONTRACT = settings.CONTRACT_RESOURCES
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
WALLET_B = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
WHEAT = 1  # resource_id for wheat


class TestFungibleLocalState(EvenniaTest):
    """Test the private local state helpers (_add_gold, _remove_gold, etc.)."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def test_add_gold(self):
        """_add_gold should increase gold on the object."""
        self.room1.db.gold = 10
        self.room1._add_gold(5)
        self.assertEqual(self.room1.get_gold(), 15)

    def test_add_gold_from_zero(self):
        """_add_gold should work when gold starts at 0."""
        self.room1.db.gold = 0
        self.room1._add_gold(25)
        self.assertEqual(self.room1.get_gold(), 25)

    def test_remove_gold(self):
        """_remove_gold should decrease gold on the object."""
        self.room1.db.gold = 20
        self.room1._remove_gold(7)
        self.assertEqual(self.room1.get_gold(), 13)

    def test_remove_gold_exact(self):
        """_remove_gold should work when removing exact amount."""
        self.room1.db.gold = 10
        self.room1._remove_gold(10)
        self.assertEqual(self.room1.get_gold(), 0)

    def test_remove_gold_insufficient_raises(self):
        """_remove_gold should raise ValueError if insufficient gold."""
        self.room1.db.gold = 5
        with self.assertRaises(ValueError):
            self.room1._remove_gold(10)

    def test_add_resource(self):
        """_add_resource should increase a resource on the object."""
        self.room1.db.resources = {WHEAT: 3}
        self.room1._add_resource(WHEAT, 5)
        self.assertEqual(self.room1.get_resource(WHEAT), 8)

    def test_add_resource_new(self):
        """_add_resource should create a new entry for a new resource."""
        self.room1.db.resources = {}
        self.room1._add_resource(WHEAT, 10)
        self.assertEqual(self.room1.get_resource(WHEAT), 10)

    def test_remove_resource(self):
        """_remove_resource should decrease a resource on the object."""
        self.room1.db.resources = {WHEAT: 15}
        self.room1._remove_resource(WHEAT, 5)
        self.assertEqual(self.room1.get_resource(WHEAT), 10)

    def test_remove_resource_exact_removes_key(self):
        """_remove_resource should remove the key when amount reaches 0."""
        self.room1.db.resources = {WHEAT: 5}
        self.room1._remove_resource(WHEAT, 5)
        self.assertEqual(self.room1.get_resource(WHEAT), 0)
        self.assertNotIn(WHEAT, self.room1.get_all_resources())

    def test_remove_resource_insufficient_raises(self):
        """_remove_resource should raise ValueError if insufficient."""
        self.room1.db.resources = {WHEAT: 3}
        with self.assertRaises(ValueError):
            self.room1._remove_resource(WHEAT, 10)


class TestFungibleClassify(EvenniaTest):
    """Test _classify_fungible, _get_wallet, and _get_character_key helpers."""

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

    def test_classify_character(self):
        from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
        self.assertEqual(FungibleInventoryMixin._classify_fungible(self.char1), "CHARACTER")

    def test_classify_account_bank(self):
        from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
        self.assertEqual(FungibleInventoryMixin._classify_fungible(self.bank), "ACCOUNT")

    def test_classify_room(self):
        from typeclasses.mixins.fungible_inventory import FungibleInventoryMixin
        self.assertEqual(FungibleInventoryMixin._classify_fungible(self.room1), "WORLD")

    def test_get_wallet_character(self):
        """Character wallet comes from account.wallet_address."""
        self.assertEqual(self.char1._get_wallet(), WALLET_A)

    def test_get_wallet_account_bank(self):
        """AccountBank wallet comes from self.wallet_address."""
        self.assertEqual(self.bank._get_wallet(), WALLET_A)

    def test_get_wallet_room(self):
        """Room wallet is the vault address."""
        self.assertEqual(self.room1._get_wallet(), VAULT)

    def test_get_character_key_character(self):
        """Character key is the character's name."""
        self.assertEqual(self.char1._get_character_key(), self.char1.key)

    def test_get_character_key_room(self):
        """Room has no character key."""
        self.assertIsNone(self.room1._get_character_key())

    def test_get_character_key_bank(self):
        """AccountBank has no character key."""
        self.assertIsNone(self.bank._get_character_key())


class TestGoldTransfers(EvenniaTest):
    """
    Test that transfer_gold_to dispatches to the correct GoldService method
    and updates local state on both source and target.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-TestAccount",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        # Initialize fungible state
        self.room1.db.gold = 0
        self.room1.db.resources = {}
        self.room2.db.gold = 0
        self.room2.db.resources = {}

    # ── Room (WORLD) → Character (CHARACTER) = pickup ──────────────

    @patch("blockchain.xrpl.services.gold.GoldService.pickup")
    def test_room_to_character_calls_pickup(self, mock_pickup):
        """Transferring gold from a room to a character = GoldService.pickup."""
        self.room1.db.gold = 50
        self.room1.transfer_gold_to(self.char1, 25)
        mock_pickup.assert_called_once_with(
            WALLET_A, 25, CHAIN_ID, GOLD_CONTRACT, VAULT, self.char1.key,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.pickup")
    def test_room_to_character_updates_local_state(self, mock_pickup):
        """Gold should move from room to character in local state."""
        self.room1.db.gold = 50
        self.char1.db.gold = 10
        self.room1.transfer_gold_to(self.char1, 25)
        self.assertEqual(self.room1.get_gold(), 25)
        self.assertEqual(self.char1.get_gold(), 35)

    # ── Character (CHARACTER) → Room (WORLD) = drop ────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.drop")
    def test_character_to_room_calls_drop(self, mock_drop):
        """Transferring gold from a character to a room = GoldService.drop."""
        self.char1.db.gold = 30
        self.char1.transfer_gold_to(self.room1, 10)
        mock_drop.assert_called_once_with(
            WALLET_A, 10, CHAIN_ID, GOLD_CONTRACT, VAULT, self.char1.key,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.drop")
    def test_character_to_room_updates_local_state(self, mock_drop):
        """Gold should move from character to room in local state."""
        self.char1.db.gold = 30
        self.char1.transfer_gold_to(self.room1, 10)
        self.assertEqual(self.char1.get_gold(), 20)
        self.assertEqual(self.room1.get_gold(), 10)

    # ── Character → Character = transfer ───────────────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.transfer")
    def test_character_to_character_calls_transfer(self, mock_transfer):
        """Transferring gold between characters = GoldService.transfer."""
        self.char1.db.gold = 100
        self.char1.transfer_gold_to(self.char2, 40)
        mock_transfer.assert_called_once_with(
            WALLET_A, self.char1.key, WALLET_B, self.char2.key,
            40, CHAIN_ID, GOLD_CONTRACT,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.transfer")
    def test_character_to_character_updates_local_state(self, mock_transfer):
        """Gold should move between characters in local state."""
        self.char1.db.gold = 100
        self.char2.db.gold = 5
        self.char1.transfer_gold_to(self.char2, 40)
        self.assertEqual(self.char1.get_gold(), 60)
        self.assertEqual(self.char2.get_gold(), 45)

    # ── Character → AccountBank (ACCOUNT) = bank ──────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_character_to_bank_calls_bank(self, mock_bank):
        """Depositing gold from character to bank = GoldService.bank."""
        self.char1.db.gold = 50
        self.bank.db.gold = 0
        self.char1.transfer_gold_to(self.bank, 20)
        mock_bank.assert_called_once_with(
            WALLET_A, 20, CHAIN_ID, GOLD_CONTRACT, self.char1.key,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_character_to_bank_updates_local_state(self, mock_bank):
        """Gold should move from character to bank in local state."""
        self.char1.db.gold = 50
        self.bank.db.gold = 0
        self.char1.transfer_gold_to(self.bank, 20)
        self.assertEqual(self.char1.get_gold(), 30)
        self.assertEqual(self.bank.get_gold(), 20)

    # ── AccountBank → Character = unbank ──────────────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_bank_to_character_calls_unbank(self, mock_unbank):
        """Withdrawing gold from bank to character = GoldService.unbank."""
        self.bank.db.gold = 100
        self.char1.db.gold = 0
        self.bank.transfer_gold_to(self.char1, 30)
        mock_unbank.assert_called_once_with(
            WALLET_A, 30, CHAIN_ID, GOLD_CONTRACT, self.char1.key,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_bank_to_character_updates_local_state(self, mock_unbank):
        """Gold should move from bank to character in local state."""
        self.bank.db.gold = 100
        self.char1.db.gold = 0
        self.bank.transfer_gold_to(self.char1, 30)
        self.assertEqual(self.bank.get_gold(), 70)
        self.assertEqual(self.char1.get_gold(), 30)

    # ── None target raises ValueError ──────────────────────────────

    def test_none_target_raises_with_helpful_message(self):
        """transfer_gold_to(None) should raise ValueError pointing to return_gold_to_reserve."""
        self.char1.db.gold = 50
        with self.assertRaises(ValueError) as ctx:
            self.char1.transfer_gold_to(None, 15)
        self.assertIn("return_gold_to_reserve", str(ctx.exception))

    # ── Unsupported transfer types ────────────────────────────────

    def test_room_to_room_moves_local_state(self):
        """WORLD → WORLD gold transfer moves local state (mob → corpse)."""
        self.room1.db.gold = 50
        self.room2.db.gold = 0
        self.room1.transfer_gold_to(self.room2, 10)
        self.assertEqual(self.room1.get_gold(), 40)
        self.assertEqual(self.room2.get_gold(), 10)

    # ── Validation ────────────────────────────────────────────────

    def test_zero_amount_raises(self):
        """Transfer of 0 gold should raise ValueError."""
        self.char1.db.gold = 50
        with self.assertRaises(ValueError):
            self.char1.transfer_gold_to(self.room1, 0)

    def test_negative_amount_raises(self):
        """Transfer of negative gold should raise ValueError."""
        self.char1.db.gold = 50
        with self.assertRaises(ValueError):
            self.char1.transfer_gold_to(self.room1, -5)


class TestGoldReceiveFromReserve(EvenniaTest):
    """
    Test that receive_gold_from_reserve dispatches to the correct
    GoldService method and updates local state.
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

    @patch("blockchain.xrpl.services.gold.GoldService.spawn")
    def test_room_receive_calls_spawn(self, mock_spawn):
        """Receiving gold into a room = GoldService.spawn."""
        self.room1.db.gold = 0
        self.room1.receive_gold_from_reserve(25)
        mock_spawn.assert_called_once_with(
            25, CHAIN_ID, GOLD_CONTRACT, VAULT,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.spawn")
    def test_room_receive_updates_local_state(self, mock_spawn):
        """Gold should be added to room."""
        self.room1.db.gold = 10
        self.room1.receive_gold_from_reserve(25)
        self.assertEqual(self.room1.get_gold(), 35)

    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    def test_character_receive_calls_craft_output(self, mock_craft):
        """Receiving gold into a character = GoldService.craft_output."""
        self.char1.db.gold = 0
        self.char1.receive_gold_from_reserve(50)
        mock_craft.assert_called_once_with(
            WALLET_A, 50, CHAIN_ID, GOLD_CONTRACT, VAULT, self.char1.key,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.craft_output")
    def test_character_receive_updates_local_state(self, mock_craft):
        """Gold should be added to character."""
        self.char1.db.gold = 10
        self.char1.receive_gold_from_reserve(50)
        self.assertEqual(self.char1.get_gold(), 60)

    @patch("blockchain.xrpl.services.gold.GoldService.reserve_to_account")
    def test_bank_receive_calls_reserve_to_account(self, mock_r2a):
        """Receiving gold into a bank = GoldService.reserve_to_account."""
        self.bank.db.gold = 0
        self.bank.receive_gold_from_reserve(75)
        mock_r2a.assert_called_once_with(
            WALLET_A, 75, CHAIN_ID, GOLD_CONTRACT, VAULT,
        )

    def test_zero_amount_raises(self):
        """Receiving 0 gold should raise ValueError."""
        with self.assertRaises(ValueError):
            self.room1.receive_gold_from_reserve(0)

    def test_negative_amount_raises(self):
        """Receiving negative gold should raise ValueError."""
        with self.assertRaises(ValueError):
            self.room1.receive_gold_from_reserve(-10)


class TestResourceTransfers(EvenniaTest):
    """
    Test that transfer_resource_to dispatches to the correct ResourceService
    method and updates local state on both source and target.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.account2.attributes.add("wallet_address", WALLET_B)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key="bank-TestAccount",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        # Initialize fungible state
        self.room1.db.gold = 0
        self.room1.db.resources = {}
        self.room2.db.gold = 0
        self.room2.db.resources = {}

    # ── Room → Character = pickup ─────────────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.pickup")
    def test_room_to_character_calls_pickup(self, mock_pickup):
        """Transferring resource from room to character = ResourceService.pickup."""
        self.room1.db.resources = {WHEAT: 20}
        self.room1.transfer_resource_to(self.char1, WHEAT, 10)
        mock_pickup.assert_called_once_with(
            WALLET_A, WHEAT, 10, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
            self.char1.key,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.pickup")
    def test_room_to_character_updates_local_state(self, mock_pickup):
        """Resource should move from room to character in local state."""
        self.room1.db.resources = {WHEAT: 20}
        self.char1.db.resources = {WHEAT: 5}
        self.room1.transfer_resource_to(self.char1, WHEAT, 10)
        self.assertEqual(self.room1.get_resource(WHEAT), 10)
        self.assertEqual(self.char1.get_resource(WHEAT), 15)

    # ── Character → Room = drop ───────────────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.drop")
    def test_character_to_room_calls_drop(self, mock_drop):
        """Transferring resource from character to room = ResourceService.drop."""
        self.char1.db.resources = {WHEAT: 15}
        self.char1.transfer_resource_to(self.room1, WHEAT, 5)
        mock_drop.assert_called_once_with(
            WALLET_A, WHEAT, 5, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
            self.char1.key,
        )

    # ── Character → Character = transfer ──────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.transfer")
    def test_character_to_character_calls_transfer(self, mock_transfer):
        """Transferring resources between characters = ResourceService.transfer."""
        self.char1.db.resources = {WHEAT: 30}
        self.char1.transfer_resource_to(self.char2, WHEAT, 12)
        mock_transfer.assert_called_once_with(
            WALLET_A, self.char1.key, WALLET_B, self.char2.key,
            WHEAT, 12, CHAIN_ID, RESOURCE_CONTRACT,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.transfer")
    def test_character_to_character_updates_local_state(self, mock_transfer):
        """Resources should move between characters in local state."""
        self.char1.db.resources = {WHEAT: 30}
        self.char2.db.resources = {WHEAT: 2}
        self.char1.transfer_resource_to(self.char2, WHEAT, 12)
        self.assertEqual(self.char1.get_resource(WHEAT), 18)
        self.assertEqual(self.char2.get_resource(WHEAT), 14)

    # ── Character → Bank = bank ───────────────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_character_to_bank_calls_bank(self, mock_bank):
        """Depositing resource to bank = ResourceService.bank."""
        self.char1.db.resources = {WHEAT: 20}
        self.bank.db.resources = {}
        self.char1.transfer_resource_to(self.bank, WHEAT, 8)
        mock_bank.assert_called_once_with(
            WALLET_A, WHEAT, 8, CHAIN_ID, RESOURCE_CONTRACT,
            self.char1.key,
        )

    # ── Bank → Character = unbank ─────────────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.unbank")
    def test_bank_to_character_calls_unbank(self, mock_unbank):
        """Withdrawing resource from bank = ResourceService.unbank."""
        self.bank.db.resources = {WHEAT: 50}
        self.char1.db.resources = {}
        self.bank.transfer_resource_to(self.char1, WHEAT, 15)
        mock_unbank.assert_called_once_with(
            WALLET_A, WHEAT, 15, CHAIN_ID, RESOURCE_CONTRACT,
            self.char1.key,
        )

    # ── None target raises ValueError ──────────────────────────────

    def test_none_target_raises_with_helpful_message(self):
        """transfer_resource_to(None) should raise ValueError pointing to return_resource_to_reserve."""
        self.char1.db.resources = {WHEAT: 20}
        with self.assertRaises(ValueError) as ctx:
            self.char1.transfer_resource_to(None, WHEAT, 5)
        self.assertIn("return_resource_to_reserve", str(ctx.exception))

    # ── Unsupported and validation ────────────────────────────────

    def test_room_to_room_moves_local_state(self):
        """WORLD → WORLD resource transfer moves local state (mob → corpse)."""
        self.room1.db.resources = {WHEAT: 50}
        self.room2.db.resources = {}
        self.room1.transfer_resource_to(self.room2, WHEAT, 10)
        self.assertEqual(self.room1.get_resource(WHEAT), 40)
        self.assertEqual(self.room2.get_resource(WHEAT), 10)

    def test_zero_amount_raises(self):
        """Transfer of 0 resources should raise ValueError."""
        self.char1.db.resources = {WHEAT: 50}
        with self.assertRaises(ValueError):
            self.char1.transfer_resource_to(self.room1, WHEAT, 0)


class TestResourceReceiveFromReserve(EvenniaTest):
    """
    Test that receive_resource_from_reserve dispatches to the correct
    ResourceService method and updates local state.
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

    @patch("blockchain.xrpl.services.resource.ResourceService.spawn")
    def test_room_receive_calls_spawn(self, mock_spawn):
        """Receiving resource into a room = ResourceService.spawn."""
        self.room1.db.resources = {}
        self.room1.receive_resource_from_reserve(WHEAT, 15)
        mock_spawn.assert_called_once_with(
            WHEAT, 15, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.spawn")
    def test_room_receive_updates_local_state(self, mock_spawn):
        """Resource should be added to room."""
        self.room1.db.resources = {WHEAT: 5}
        self.room1.receive_resource_from_reserve(WHEAT, 15)
        self.assertEqual(self.room1.get_resource(WHEAT), 20)

    @patch("blockchain.xrpl.services.resource.ResourceService.craft_output")
    def test_character_receive_calls_craft_output(self, mock_craft):
        """Receiving resource into a character = ResourceService.craft_output."""
        self.char1.db.resources = {}
        self.char1.receive_resource_from_reserve(WHEAT, 10)
        mock_craft.assert_called_once_with(
            WALLET_A, WHEAT, 10, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
            self.char1.key,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.reserve_to_account")
    def test_bank_receive_calls_reserve_to_account(self, mock_r2a):
        """Receiving resource into a bank = ResourceService.reserve_to_account."""
        self.bank.db.resources = {}
        self.bank.receive_resource_from_reserve(WHEAT, 20)
        mock_r2a.assert_called_once_with(
            WALLET_A, WHEAT, 20, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
        )

    def test_zero_amount_raises(self):
        """Receiving 0 resources should raise ValueError."""
        with self.assertRaises(ValueError):
            self.room1.receive_resource_from_reserve(WHEAT, 0)


class TestGoldReturnToReserve(EvenniaTest):
    """
    Test that return_gold_to_reserve dispatches to the correct GoldService
    method based on source type, and updates local state.
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

    # ── CHARACTER → RESERVE = craft_input ──────────────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.craft_input")
    def test_character_calls_craft_input(self, mock_craft):
        """Character returning gold to reserve = GoldService.craft_input."""
        self.char1.db.gold = 50
        self.char1.return_gold_to_reserve(15)
        mock_craft.assert_called_once_with(
            WALLET_A, 15, CHAIN_ID, GOLD_CONTRACT, VAULT, self.char1.key,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.craft_input")
    def test_character_updates_local_state(self, mock_craft):
        """Gold should be removed from character."""
        self.char1.db.gold = 50
        self.char1.return_gold_to_reserve(15)
        self.assertEqual(self.char1.get_gold(), 35)

    # ── WORLD → RESERVE = despawn ──────────────────────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.despawn")
    def test_room_calls_despawn(self, mock_despawn):
        """Room returning gold to reserve = GoldService.despawn."""
        self.room1.db.gold = 40
        self.room1.return_gold_to_reserve(10)
        mock_despawn.assert_called_once_with(
            10, CHAIN_ID, GOLD_CONTRACT, VAULT,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.despawn")
    def test_room_updates_local_state(self, mock_despawn):
        """Gold should be removed from room."""
        self.room1.db.gold = 40
        self.room1.return_gold_to_reserve(10)
        self.assertEqual(self.room1.get_gold(), 30)

    # ── ACCOUNT → RESERVE = account_to_reserve ─────────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.account_to_reserve")
    def test_bank_calls_account_to_reserve(self, mock_a2r):
        """Bank returning gold to reserve = GoldService.account_to_reserve."""
        self.bank.db.gold = 100
        self.bank.return_gold_to_reserve(25)
        mock_a2r.assert_called_once_with(
            WALLET_A, 25, CHAIN_ID, GOLD_CONTRACT, VAULT,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.account_to_reserve")
    def test_bank_updates_local_state(self, mock_a2r):
        """Gold should be removed from bank."""
        self.bank.db.gold = 100
        self.bank.return_gold_to_reserve(25)
        self.assertEqual(self.bank.get_gold(), 75)

    # ── Validation ─────────────────────────────────────────────────

    def test_zero_amount_raises(self):
        """Returning 0 gold should raise ValueError."""
        self.char1.db.gold = 50
        with self.assertRaises(ValueError):
            self.char1.return_gold_to_reserve(0)

    def test_negative_amount_raises(self):
        """Returning negative gold should raise ValueError."""
        self.char1.db.gold = 50
        with self.assertRaises(ValueError):
            self.char1.return_gold_to_reserve(-5)


class TestResourceReturnToReserve(EvenniaTest):
    """
    Test that return_resource_to_reserve dispatches to the correct
    ResourceService method based on source type, and updates local state.
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

    # ── CHARACTER → RESERVE = craft_input ──────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.craft_input")
    def test_character_calls_craft_input(self, mock_craft):
        """Character returning resource to reserve = ResourceService.craft_input."""
        self.char1.db.resources = {WHEAT: 20}
        self.char1.return_resource_to_reserve(WHEAT, 5)
        mock_craft.assert_called_once_with(
            WALLET_A, WHEAT, 5, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
            self.char1.key,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.craft_input")
    def test_character_updates_local_state(self, mock_craft):
        """Resource should be removed from character."""
        self.char1.db.resources = {WHEAT: 20}
        self.char1.return_resource_to_reserve(WHEAT, 5)
        self.assertEqual(self.char1.get_resource(WHEAT), 15)

    # ── WORLD → RESERVE = despawn ──────────────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.despawn")
    def test_room_calls_despawn(self, mock_despawn):
        """Room returning resource to reserve = ResourceService.despawn."""
        self.room1.db.resources = {WHEAT: 30}
        self.room1.return_resource_to_reserve(WHEAT, 10)
        mock_despawn.assert_called_once_with(
            WHEAT, 10, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.despawn")
    def test_room_updates_local_state(self, mock_despawn):
        """Resource should be removed from room."""
        self.room1.db.resources = {WHEAT: 30}
        self.room1.return_resource_to_reserve(WHEAT, 10)
        self.assertEqual(self.room1.get_resource(WHEAT), 20)

    # ── ACCOUNT → RESERVE = account_to_reserve ─────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.account_to_reserve")
    def test_bank_calls_account_to_reserve(self, mock_a2r):
        """Bank returning resource to reserve = ResourceService.account_to_reserve."""
        self.bank.db.resources = {WHEAT: 40}
        self.bank.return_resource_to_reserve(WHEAT, 10)
        mock_a2r.assert_called_once_with(
            WALLET_A, WHEAT, 10, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.account_to_reserve")
    def test_bank_updates_local_state(self, mock_a2r):
        """Resource should be removed from bank."""
        self.bank.db.resources = {WHEAT: 40}
        self.bank.return_resource_to_reserve(WHEAT, 10)
        self.assertEqual(self.bank.get_resource(WHEAT), 30)

    # ── Validation ─────────────────────────────────────────────────

    def test_zero_amount_raises(self):
        """Returning 0 resources should raise ValueError."""
        self.char1.db.resources = {WHEAT: 20}
        with self.assertRaises(ValueError):
            self.char1.return_resource_to_reserve(WHEAT, 0)

    def test_negative_amount_raises(self):
        """Returning negative resources should raise ValueError."""
        self.char1.db.resources = {WHEAT: 20}
        with self.assertRaises(ValueError):
            self.char1.return_resource_to_reserve(WHEAT, -3)


class TestChainDepositWithdraw(EvenniaTest):
    """
    Test that chain deposit/withdraw methods on AccountBank dispatch to the
    correct service methods and update local state.

    These methods are the ACCOUNT-level chain boundary: called from inputfuncs
    after tx confirmations to credit/debit the player's bank.
    """

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

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

    # ── deposit_gold_from_chain ─────────────────────────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.deposit_from_chain")
    def test_deposit_gold_calls_service(self, mock_deposit):
        """deposit_gold_from_chain should call GoldService.deposit_from_chain."""
        self.bank.db.gold = 0
        self.bank.deposit_gold_from_chain(100, "0xtxhash1")
        mock_deposit.assert_called_once_with(
            WALLET_A, 100, VAULT, "0xtxhash1",
        )

    @patch("blockchain.xrpl.services.gold.GoldService.deposit_from_chain")
    def test_deposit_gold_updates_local_state(self, mock_deposit):
        """deposit_gold_from_chain should add gold to the bank."""
        self.bank.db.gold = 50
        self.bank.deposit_gold_from_chain(100, "0xtxhash1")
        self.assertEqual(self.bank.get_gold(), 150)

    # ── withdraw_gold_to_chain ──────────────────────────────────────

    @patch("blockchain.xrpl.services.gold.GoldService.withdraw_to_chain")
    def test_withdraw_gold_calls_service(self, mock_withdraw):
        """withdraw_gold_to_chain should call GoldService.withdraw_to_chain."""
        self.bank.db.gold = 200
        self.bank.withdraw_gold_to_chain(75, "0xtxhash2")
        mock_withdraw.assert_called_once_with(
            WALLET_A, 75, VAULT, "0xtxhash2",
        )

    @patch("blockchain.xrpl.services.gold.GoldService.withdraw_to_chain")
    def test_withdraw_gold_updates_local_state(self, mock_withdraw):
        """withdraw_gold_to_chain should remove gold from the bank."""
        self.bank.db.gold = 200
        self.bank.withdraw_gold_to_chain(75, "0xtxhash2")
        self.assertEqual(self.bank.get_gold(), 125)

    @patch("blockchain.xrpl.services.gold.GoldService.withdraw_to_chain")
    def test_withdraw_gold_insufficient_raises(self, mock_withdraw):
        """withdraw_gold_to_chain should raise if bank has insufficient gold."""
        self.bank.db.gold = 10
        with self.assertRaises(ValueError):
            self.bank.withdraw_gold_to_chain(50, "0xtxhash")

    # ── deposit_resource_from_chain ─────────────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.deposit_from_chain")
    def test_deposit_resource_calls_service(self, mock_deposit):
        """deposit_resource_from_chain should call ResourceService.deposit_from_chain."""
        self.bank.db.resources = {}
        self.bank.deposit_resource_from_chain(WHEAT, 25, "0xtxhash3")
        mock_deposit.assert_called_once_with(
            WALLET_A, WHEAT, 25, VAULT, "0xtxhash3",
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.deposit_from_chain")
    def test_deposit_resource_updates_local_state(self, mock_deposit):
        """deposit_resource_from_chain should add resource to the bank."""
        self.bank.db.resources = {WHEAT: 5}
        self.bank.deposit_resource_from_chain(WHEAT, 25, "0xtxhash3")
        self.assertEqual(self.bank.get_resource(WHEAT), 30)

    # ── withdraw_resource_to_chain ──────────────────────────────────

    @patch("blockchain.xrpl.services.resource.ResourceService.withdraw_to_chain")
    def test_withdraw_resource_calls_service(self, mock_withdraw):
        """withdraw_resource_to_chain should call ResourceService.withdraw_to_chain."""
        self.bank.db.resources = {WHEAT: 40}
        self.bank.withdraw_resource_to_chain(WHEAT, 15, "0xtxhash4")
        mock_withdraw.assert_called_once_with(
            WALLET_A, WHEAT, 15, VAULT, "0xtxhash4",
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.withdraw_to_chain")
    def test_withdraw_resource_updates_local_state(self, mock_withdraw):
        """withdraw_resource_to_chain should remove resource from the bank."""
        self.bank.db.resources = {WHEAT: 40}
        self.bank.withdraw_resource_to_chain(WHEAT, 15, "0xtxhash4")
        self.assertEqual(self.bank.get_resource(WHEAT), 25)

    @patch("blockchain.xrpl.services.resource.ResourceService.withdraw_to_chain")
    def test_withdraw_resource_insufficient_raises(self, mock_withdraw):
        """withdraw_resource_to_chain should raise if bank has insufficient resource."""
        self.bank.db.resources = {WHEAT: 3}
        with self.assertRaises(ValueError):
            self.bank.withdraw_resource_to_chain(WHEAT, 10, "0xtxhash")


class TestReadOnlyQueries(EvenniaTest):
    """Test the read-only query methods."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_get_gold_default(self):
        """get_gold returns 0 when no gold set."""
        self.room1.db.gold = None
        self.assertEqual(self.room1.get_gold(), 0)

    def test_has_gold_true(self):
        self.char1.db.gold = 50
        self.assertTrue(self.char1.has_gold(50))

    def test_has_gold_false(self):
        self.char1.db.gold = 10
        self.assertFalse(self.char1.has_gold(50))

    def test_get_resource_default(self):
        """get_resource returns 0 for missing resource."""
        self.room1.db.resources = {}
        self.assertEqual(self.room1.get_resource(WHEAT), 0)

    def test_has_resource_true(self):
        self.char1.db.resources = {WHEAT: 15}
        self.assertTrue(self.char1.has_resource(WHEAT, 10))

    def test_has_resource_false(self):
        self.char1.db.resources = {WHEAT: 3}
        self.assertFalse(self.char1.has_resource(WHEAT, 10))

    def test_get_all_resources_returns_copy(self):
        """get_all_resources should return a copy, not the original dict."""
        self.char1.db.resources = {WHEAT: 10}
        result = self.char1.get_all_resources()
        result[999] = 50  # mutate the copy
        self.assertNotIn(999, self.char1.db.resources)
