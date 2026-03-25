"""
Tests for CmdDeposit — verifies depositing gold, resources, and NFT items
from character inventory into the AccountBank.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.bank.cmd_deposit import CmdDeposit


CHAIN_ID = settings.BLOCKCHAIN_CHAIN_ID
CONTRACT_NFT = settings.CONTRACT_NFT
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdDepositGold(EvenniaCommandTest):
    """Test depositing gold into the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 100
        self.char1.db.resources = {}
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.bank.db.gold = 0
        self.bank.db.resources = {}
        self.account.db.bank = self.bank

    def test_deposit_no_args(self):
        """deposit with no args should show usage."""
        self.call(CmdDeposit(), "", "Usage:")

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_deposit_gold_default_one(self, mock_bank):
        """deposit gold should deposit 1 by default."""
        self.call(CmdDeposit(), "gold", "You deposit 1")
        self.assertEqual(self.char1.get_gold(), 99)
        self.assertEqual(self.bank.get_gold(), 1)

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_deposit_gold_amount(self, mock_bank):
        """deposit gold 50 should deposit 50."""
        self.call(CmdDeposit(), "gold 50", "You deposit 50")
        self.assertEqual(self.char1.get_gold(), 50)
        self.assertEqual(self.bank.get_gold(), 50)

    @patch("blockchain.xrpl.services.gold.GoldService.bank")
    def test_deposit_gold_all(self, mock_bank):
        """deposit gold all should deposit everything."""
        self.call(CmdDeposit(), "gold all", "You deposit 100")
        self.assertEqual(self.char1.get_gold(), 0)
        self.assertEqual(self.bank.get_gold(), 100)

    def test_deposit_gold_insufficient(self):
        """deposit more gold than you have should show error."""
        self.char1.db.gold = 10
        self.call(CmdDeposit(), "gold 50", "You only have 10")

    def test_deposit_gold_none(self):
        """deposit gold when you have none should show error."""
        self.char1.db.gold = 0
        self.call(CmdDeposit(), "gold", "You don't have any gold")


class TestCmdDepositResource(EvenniaCommandTest):
    """Test depositing resources into the bank."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {1: 20}  # 20 wheat
        self.bank = create.create_object(
            "typeclasses.accounts.account_bank.AccountBank",
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.bank.db.gold = 0
        self.bank.db.resources = {}
        self.account.db.bank = self.bank

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_deposit_resource_amount(self, mock_bank):
        """deposit wheat 5 should deposit 5 wheat."""
        self.call(CmdDeposit(), "wheat 5", "You deposit 5")
        self.assertEqual(self.char1.get_resource(1), 15)
        self.assertEqual(self.bank.get_resource(1), 5)

    @patch("blockchain.xrpl.services.resource.ResourceService.bank")
    def test_deposit_resource_all(self, mock_bank):
        """deposit wheat all should deposit all wheat."""
        self.call(CmdDeposit(), "wheat all", "You deposit 20")
        self.assertEqual(self.char1.get_resource(1), 0)
        self.assertEqual(self.bank.get_resource(1), 20)

    def test_deposit_resource_insufficient(self):
        """deposit more resource than you have should show error."""
        self.char1.db.resources = {1: 2}
        self.call(CmdDeposit(), "wheat 10", "You only have 2")


class TestCmdDepositNFT(EvenniaCommandTest):
    """Test depositing NFT items into the bank."""

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

        # Create a takeable NFT in character inventory (bypass hooks)
        self.sword = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Iron Sword",
            nohome=True,
        )
        self.sword.token_id = 42
        self.sword.chain_id = CHAIN_ID
        self.sword.contract_address = CONTRACT_NFT
        self.sword.db_location = self.char1
        self.sword.save(update_fields=["db_location"])

    @patch("blockchain.xrpl.services.nft.NFTService.bank")
    def test_deposit_nft(self, mock_bank):
        """deposit by dbref should move NFT to bank."""
        self.call(CmdDeposit(), str(self.sword.id), "You deposit Iron Sword")
        self.assertEqual(self.sword.location, self.bank)

    def test_deposit_nft_not_found(self):
        """deposit nonexistent token ID should show error."""
        self.call(CmdDeposit(), "999", "You aren't carrying an item with ID #999")

    def test_deposit_unknown_arg(self):
        """deposit with unrecognized argument tries item search."""
        self.call(CmdDeposit(), "banana", "You aren't carrying")
