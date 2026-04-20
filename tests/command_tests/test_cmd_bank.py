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


class TestCmdBankShips(EvenniaCommandTest):
    """
    OOC bank command must show ships under their own |wShips:|n heading
    using get_owned_display() (which includes the berth location), and
    must NOT leak ships into the |wItems:|n section.
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
            key=f"bank-{self.account.key}",
            nohome=True,
        )
        self.bank.wallet_address = WALLET_A
        self.account.db.bank = self.bank

        # Real ship in the bank (bypass NFT mirror via db_location set).
        from unittest.mock import patch
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"):
            self.ship = create.create_object(
                "typeclasses.items.untakeables.ship_nft_item.ShipNFTItem",
                key="The Grey Widow",
                nohome=True,
            )
            self.ship.token_id = 555
            self.ship.db.ship_tier = 1  # Cog
            self.ship.set_world_location(self.room1)
        self.ship.db_location = self.bank
        self.ship.save(update_fields=["db_location"])

    def test_bank_shows_ship_under_ships_heading(self):
        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("Ships", result)
        self.assertIn("The Grey Widow", result)

    def test_bank_ship_includes_berth_location(self):
        """get_owned_display() emits 'berthed at <room>' inline."""
        result = self.call(CmdBank(), "", caller=self.account)
        self.assertIn("berthed at", result)
        self.assertIn(self.room1.key, result)

    def test_bank_ship_does_not_appear_in_items_section(self):
        """
        Latent bug fix: BaseNFTItem filter previously included WorldAnchored
        subclasses, so a banked ship leaked into the Items section AND the
        Ships placeholder rendered empty. Verify ships only appear once.
        """
        result = self.call(CmdBank(), "", caller=self.account)
        # The ship name should appear exactly once (in the Ships section)
        self.assertEqual(result.count("The Grey Widow"), 1)
