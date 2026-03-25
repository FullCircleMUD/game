"""
Tests for CmdJunk — verifies the junk command correctly calls
return_gold_to_sink, return_resource_to_sink, and item.delete()
for NFTs.

Junk uses strict parsing (_bank_parse) — type-first for fungibles,
token ID only for NFTs. No fuzzy name matching.

Uses EvenniaCommandTest which provides the self.call() helper for
testing commands, including yield-based confirmation prompts via inputs=[].
"""

from unittest.mock import patch, MagicMock

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_junk import CmdJunk


VAULT = settings.XRPL_VAULT_ADDRESS
CHAIN_ID = settings.BLOCKCHAIN_CHAIN_ID
GOLD_CONTRACT = settings.CONTRACT_GOLD
RESOURCE_CONTRACT = settings.CONTRACT_RESOURCES
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
TOKEN_ID = 42
CONTRACT_NFT = settings.CONTRACT_NFT


class TestCmdJunkGold(EvenniaCommandTest):
    """Test junking gold via the junk command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 100
        self.char1.db.resources = {}

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_junk_gold_calls_return_to_reserve(self, mock_craft):
        """junk gold 50 should call return_gold_to_reserve → GoldService.sink."""
        self.call(CmdJunk(), "gold 50", inputs=["y"])
        mock_craft.assert_called_once_with(
            WALLET_A, 50, CHAIN_ID, GOLD_CONTRACT, VAULT, self.char1.key,
        )

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_junk_gold_updates_local_state(self, mock_craft):
        """After junking 50 gold, character should have 50 left."""
        self.call(CmdJunk(), "gold 50", inputs=["y"])
        self.assertEqual(self.char1.get_gold(), 50)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_junk_gold_confirm_no_cancels(self, mock_craft):
        """Answering 'n' to confirmation should cancel and not call service."""
        self.call(CmdJunk(), "gold 50", inputs=["n"])
        mock_craft.assert_not_called()
        self.assertEqual(self.char1.get_gold(), 100)

    def test_junk_gold_insufficient(self):
        """Junking more gold than you have should show error."""
        self.char1.db.gold = 10
        self.call(CmdJunk(), "gold 50", "You only have 10 gold.")

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_junk_gold_shows_destroyed_message(self, mock_craft):
        """Junk command should show 'destroyed' message on success."""
        self.call(CmdJunk(), "gold 50", "50 coins of Gold destroyed.", inputs=["y"])

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_junk_gold_all(self, mock_craft):
        """junk gold all should destroy all gold."""
        self.call(CmdJunk(), "gold all", inputs=["y"])
        mock_craft.assert_called_once_with(
            WALLET_A, 100, CHAIN_ID, GOLD_CONTRACT, VAULT, self.char1.key,
        )
        self.assertEqual(self.char1.get_gold(), 0)


class TestCmdJunkResource(EvenniaCommandTest):
    """Test junking resources via the junk command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {1: 20}  # 20 wheat

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_junk_resource_calls_return_to_reserve(self, mock_craft):
        """junk wheat 5 should call return_resource_to_reserve → ResourceService.sink."""
        self.call(CmdJunk(), "wheat 5", inputs=["y"])
        mock_craft.assert_called_once_with(
            WALLET_A, 1, 5, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
            self.char1.key,
        )

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_junk_resource_updates_local_state(self, mock_craft):
        """After junking 5 wheat, character should have 15 left."""
        self.call(CmdJunk(), "wheat 5", inputs=["y"])
        self.assertEqual(self.char1.get_resource(1), 15)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_junk_resource_confirm_no_cancels(self, mock_craft):
        """Answering 'n' to confirmation should cancel."""
        self.call(CmdJunk(), "wheat 5", inputs=["n"])
        mock_craft.assert_not_called()
        self.assertEqual(self.char1.get_resource(1), 20)

    def test_junk_resource_insufficient(self):
        """Junking more resource than you have should show error."""
        self.char1.db.resources = {1: 2}
        self.call(CmdJunk(), "wheat 5", "You only have 2")

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_junk_resource_all(self, mock_craft):
        """junk wheat all should destroy all wheat."""
        self.call(CmdJunk(), "wheat all", inputs=["y"])
        mock_craft.assert_called_once_with(
            WALLET_A, 1, 20, CHAIN_ID, RESOURCE_CONTRACT, VAULT,
            self.char1.key,
        )
        self.assertEqual(self.char1.get_resource(1), 0)


class TestCmdJunkNFT(EvenniaCommandTest):
    """Test junking NFT items via the junk command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Create an NFT item in character's inventory (bypass hooks)
        self.sword = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Iron Sword",
            nohome=True,
        )
        self.sword.token_id = TOKEN_ID
        self.sword.chain_id = CHAIN_ID
        self.sword.contract_address = CONTRACT_NFT
        # Place directly in inventory bypassing at_post_move
        self.sword.db_location = self.char1
        self.sword.save(update_fields=["db_location"])

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_junk_nft_by_item_id(self, mock_craft):
        """junk #<id> should call item.delete() → at_object_delete → NFTService.craft_input."""
        self.call(CmdJunk(), f"#{self.sword.id}", inputs=["y"])
        mock_craft.assert_called_once()

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_junk_nft_by_bare_number(self, mock_craft):
        """junk <id> should also work (bare number = item ID)."""
        self.call(CmdJunk(), str(self.sword.id), inputs=["y"])
        mock_craft.assert_called_once()

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_junk_nft_removes_from_inventory(self, mock_craft):
        """After junking, item should be gone from inventory."""
        self.call(CmdJunk(), f"#{self.sword.id}", inputs=["y"])
        from typeclasses.items.base_nft_item import BaseNFTItem
        nft_contents = [
            obj for obj in self.char1.contents
            if isinstance(obj, BaseNFTItem)
        ]
        self.assertEqual(len(nft_contents), 0)

    @patch("blockchain.xrpl.services.nft.NFTService.craft_input")
    def test_junk_nft_confirm_no_cancels(self, mock_craft):
        """Answering 'n' should cancel and leave item in inventory."""
        self.call(CmdJunk(), f"#{self.sword.id}", inputs=["n"])
        mock_craft.assert_not_called()
        self.assertIn(self.sword, self.char1.contents)

    def test_junk_nft_not_found(self):
        """Junking a token ID you don't have should show error."""
        self.call(CmdJunk(), "#999", "You aren't carrying an item with ID #999.")

    def test_junk_nft_name_rejected(self):
        """Junking by name should be rejected (strict mode)."""
        self.call(CmdJunk(), "Iron Sword", "Junk what? Use exact names or token IDs.")

    def test_junk_no_args(self):
        """Junk with no arguments should show usage."""
        self.call(CmdJunk(), "", "Usage:")
