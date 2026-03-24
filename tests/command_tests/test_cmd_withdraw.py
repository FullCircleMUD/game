"""
Tests for CmdWithdraw — verifies withdrawing gold, resources, and NFT items
from the AccountBank into character inventory.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.bank.cmd_withdraw import CmdWithdraw


CHAIN_ID = settings.BLOCKCHAIN_CHAIN_ID
CONTRACT_NFT = settings.CONTRACT_NFT
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdWithdrawGold(EvenniaCommandTest):
    """Test withdrawing gold from the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.bank.db.gold = 100
        self.bank.db.resources = {}
        self.account.db.bank = self.bank

    def test_withdraw_no_args(self):
        """withdraw with no args should show usage."""
        self.call(CmdWithdraw(), "", "Usage:")

    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_withdraw_gold_default_one(self, mock_unbank):
        """withdraw gold should withdraw 1 by default."""
        self.call(CmdWithdraw(), "gold", "You withdraw 1")
        self.assertEqual(self.char1.get_gold(), 1)
        self.assertEqual(self.bank.get_gold(), 99)

    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_withdraw_gold_amount(self, mock_unbank):
        """withdraw gold 50 should withdraw 50."""
        self.call(CmdWithdraw(), "gold 50", "You withdraw 50")
        self.assertEqual(self.char1.get_gold(), 50)
        self.assertEqual(self.bank.get_gold(), 50)

    @patch("blockchain.xrpl.services.gold.GoldService.unbank")
    def test_withdraw_gold_all(self, mock_unbank):
        """withdraw gold all should withdraw everything."""
        self.call(CmdWithdraw(), "gold all", "You withdraw 100")
        self.assertEqual(self.char1.get_gold(), 100)
        self.assertEqual(self.bank.get_gold(), 0)

    def test_withdraw_gold_insufficient(self):
        """withdraw more gold than available should show error."""
        self.bank.db.gold = 10
        self.call(CmdWithdraw(), "gold 50", "Your bank only has 10")

    def test_withdraw_gold_none(self):
        """withdraw gold when bank has none should show error."""
        self.bank.db.gold = 0
        self.call(CmdWithdraw(), "gold", "You don't have any gold")


class TestCmdWithdrawResource(EvenniaCommandTest):
    """Test withdrawing resources from the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.bank.db.gold = 0
        self.bank.db.resources = {1: 20}  # 20 wheat
        self.account.db.bank = self.bank

    @patch("blockchain.xrpl.services.resource.ResourceService.unbank")
    def test_withdraw_resource_amount(self, mock_unbank):
        """withdraw wheat 5 should withdraw 5 wheat."""
        self.call(CmdWithdraw(), "wheat 5", "You withdraw 5")
        self.assertEqual(self.char1.get_resource(1), 5)
        self.assertEqual(self.bank.get_resource(1), 15)

    @patch("blockchain.xrpl.services.resource.ResourceService.unbank")
    def test_withdraw_resource_all(self, mock_unbank):
        """withdraw wheat all should withdraw all wheat."""
        self.call(CmdWithdraw(), "wheat all", "You withdraw 20")
        self.assertEqual(self.char1.get_resource(1), 20)
        self.assertEqual(self.bank.get_resource(1), 0)

    def test_withdraw_resource_insufficient(self):
        """withdraw more resource than available should show error."""
        self.bank.db.resources = {1: 2}
        self.call(CmdWithdraw(), "wheat 10", "Your bank only has 2")

    def test_withdraw_resource_none(self):
        """withdraw resource when bank has none should show error."""
        self.bank.db.resources = {}
        self.call(CmdWithdraw(), "wheat", "You don't have any Wheat")


class TestCmdWithdrawNFT(EvenniaCommandTest):
    """Test withdrawing NFT items from the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.account.db.bank = self.bank

        # Create a takeable NFT in the bank (bypass hooks)
        self.sword = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Iron Sword",
            nohome=True,
        )
        self.sword.token_id = 42
        self.sword.chain_id = CHAIN_ID
        self.sword.contract_address = CONTRACT_NFT
        self.sword.db_location = self.bank
        self.sword.save(update_fields=["db_location"])

    @patch("blockchain.xrpl.services.nft.NFTService.unbank")
    def test_withdraw_nft(self, mock_unbank):
        """withdraw 42 should move NFT to character."""
        self.call(CmdWithdraw(), "42", "You withdraw Iron Sword")
        self.assertEqual(self.sword.location, self.char1)

    def test_withdraw_nft_not_found(self):
        """withdraw nonexistent token ID should show error."""
        self.call(CmdWithdraw(), "999", "No item with ID #999")

    def test_withdraw_untakeable_nft(self):
        """withdraw an WorldAnchoredNFTItem should be blocked."""
        horse = create.create_object(
            "typeclasses.items.untakeables.world_anchored_nft_item.WorldAnchoredNFTItem",
            key="Horse",
            nohome=True,
        )
        horse.token_id = 99
        horse.chain_id = CHAIN_ID
        horse.contract_address = CONTRACT_NFT
        horse.db_location = self.bank
        horse.save(update_fields=["db_location"])

        self.call(CmdWithdraw(), "99", "That item cannot be withdrawn")
        self.assertEqual(horse.location, self.bank)

    def test_withdraw_unknown_arg(self):
        """withdraw with unrecognized argument tries item search."""
        self.call(CmdWithdraw(), "banana", "No item matching")
