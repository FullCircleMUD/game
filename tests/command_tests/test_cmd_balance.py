"""
Tests for CmdBalance — verifies bank balance display for gold, resources,
takeable NFT items, and untakeable NFT items.

Uses EvenniaCommandTest which provides self.call() for testing commands.
Note: self.call() strips ANSI codes and uses startswith() for msg matching.
"""

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.bank.cmd_balance import CmdBalance


CHAIN_ID = settings.BLOCKCHAIN_CHAIN_ID
CONTRACT_NFT = settings.CONTRACT_NFT
WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdBalanceEmpty(EvenniaCommandTest):
    """Test balance when bank is empty."""

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

    def test_balance_empty(self):
        """balance with empty bank should show empty message."""
        result = self.call(CmdBalance(), "")
        self.assertIn("empty", result)

    def test_balance_all_empty(self):
        """balance all with empty bank should show empty message."""
        result = self.call(CmdBalance(), "all")
        self.assertIn("empty", result)


class TestCmdBalanceGoldAndResources(EvenniaCommandTest):
    """Test balance display for gold and resources."""

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

    def test_balance_gold(self):
        """balance should show gold amount."""
        self.bank.db.gold = 500
        result = self.call(CmdBalance(), "")
        self.assertIn("500", result)
        self.assertIn("Gold", result)

    def test_balance_resources(self):
        """balance should show resources."""
        self.bank.db.resources = {1: 20}  # 20 wheat
        result = self.call(CmdBalance(), "")
        self.assertIn("Wheat", result)
        self.assertIn("20", result)

    def test_balance_gold_and_resources(self):
        """balance should show both gold and resources."""
        self.bank.db.gold = 100
        self.bank.db.resources = {1: 10, 4: 5}  # wheat and iron ore
        result = self.call(CmdBalance(), "")
        self.assertIn("100", result)
        self.assertIn("Wheat", result)
        self.assertIn("Iron Ore", result)


class TestCmdBalanceNFTItems(EvenniaCommandTest):
    """Test balance display for NFT items."""

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

    def test_balance_shows_takeable_nft(self):
        """balance should show takeable NFT items."""
        result = self.call(CmdBalance(), "")
        self.assertIn("Iron Sword", result)

    def test_balance_shows_nft_token_id(self):
        """balance should show dbref for NFT items."""
        result = self.call(CmdBalance(), "")
        self.assertIn(f"#{self.sword.id}", result)


class TestCmdBalanceUntakeableItems(EvenniaCommandTest):
    """Test balance display for untakeable NFT items."""

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

        # Create an untakeable NFT in the bank (bypass hooks)
        self.horse = create.create_object(
            "typeclasses.items.untakeables.world_anchored_nft_item.WorldAnchoredNFTItem",
            key="Horse",
            nohome=True,
        )
        self.horse.token_id = 99
        self.horse.chain_id = CHAIN_ID
        self.horse.contract_address = CONTRACT_NFT
        self.horse.db_location = self.bank
        self.horse.save(update_fields=["db_location"])

    def test_balance_hides_untakeable_by_default(self):
        """balance should not show untakeable items in the main listing."""
        result = self.call(CmdBalance(), "")
        self.assertNotIn("Horse", result)

    def test_balance_hints_at_untakeables(self):
        """balance should hint that other items exist."""
        result = self.call(CmdBalance(), "")
        self.assertIn("other item", result)

    def test_balance_all_shows_untakeable(self):
        """balance all should show untakeable items."""
        result = self.call(CmdBalance(), "all")
        self.assertIn("Horse", result)

    def test_balance_all_shows_cannot_withdraw_label(self):
        """balance all should label untakeables as not withdrawable here."""
        result = self.call(CmdBalance(), "all")
        self.assertIn("cannot be withdrawn", result)


class TestCmdBalanceEnsureBank(EvenniaCommandTest):
    """Test that balance creates a bank for accounts that don't have one."""

    room_typeclass = "typeclasses.terrain.rooms.room_bank.RoomBank"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Deliberately do NOT create a bank — simulates superuser edge case
        self.account.db.bank = None

    def test_balance_creates_bank_if_missing(self):
        """balance should lazy-create a bank for accounts without one."""
        self.call(CmdBalance(), "")
        self.assertIsNotNone(self.account.db.bank)

    def test_balance_created_bank_has_wallet(self):
        """Lazy-created bank should have the account's wallet address."""
        self.call(CmdBalance(), "")
        bank = self.account.db.bank
        self.assertEqual(bank.wallet_address, WALLET_A)
