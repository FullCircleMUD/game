"""
Tests for CmdBank — displays account bank contents at account level.

Note: self.call() uses startswith() matching when msg is passed as a
positional arg. Since CmdBank wraps output in a header/footer, we use
`result = self.call(...)` and then `self.assertIn()` instead.
"""

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.account_cmds.cmd_bank import CmdBank


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdBankEmpty(EvenniaCommandTest):
    """Test bank display when bank is empty."""

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
        self.bank.db.gold = 0
        self.bank.db.resources = {}
        self.account.db.bank = self.bank

    def test_bank_empty(self):
        """bank with empty account should show empty message."""
        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("Your bank is empty.", result)


class TestCmdBankContents(EvenniaCommandTest):
    """Test bank display with various contents."""

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
        self.bank.db.gold = 0
        self.bank.db.resources = {}
        self.account.db.bank = self.bank

    def test_bank_gold(self):
        """bank should display gold balance."""
        self.bank.db.gold = 50
        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("Gold: 50", result)

    def test_bank_resource(self):
        """bank should display resource balances."""
        self.bank.db.resources = {1: 20}
        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("Wheat: 20", result)

    def test_bank_nft(self):
        """bank should display NFT items with token IDs."""
        sword = create.create_object(
            "typeclasses.items.base_nft_item.BaseNFTItem",
            key="Iron Sword",
            nohome=True,
        )
        sword.token_id = 42
        sword.db_location = self.bank
        sword.save(update_fields=["db_location"])

        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("Iron Sword", result)

    def test_bank_shows_character_warning(self):
        """bank should warn about character items not being shown."""
        self.bank.db.gold = 10
        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("Items carried by your characters are not shown here.", result)

    def test_bank_shows_export_hint(self):
        """bank should show export usage hint."""
        self.bank.db.gold = 10
        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("export", result)
