"""
Tests for CmdBalance — verifies bank balance display for gold, resources,
items, ships (world-anchored), and that pets stay hidden.

Uses EvenniaCommandTest which provides self.call() for testing commands.
Note: self.call() strips ANSI codes and uses startswith() for msg matching.
"""

from unittest.mock import patch

from django.conf import settings

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.room_specific_cmds.bank.cmd_balance import CmdBalance


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


class TestCmdBalanceWorldAnchoredItems(EvenniaCommandTest):
    """
    Test balance display for world-anchored items (ships, future property).

    These are now shown by default in their own |wShips:|n subsection,
    using get_owned_display() to render the berth location inline.
    """

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

        # Create a real ship in the bank (bypass NFT hooks via db_location).
        # Patch update_metadata so set_world_location doesn't try to write
        # to a non-existent mirror row.
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"):
            self.ship = create.create_object(
                "typeclasses.items.untakeables.ship_nft_item.ShipNFTItem",
                key="The Grey Widow",
                nohome=True,
            )
            self.ship.token_id = 99
            self.ship.db.ship_tier = 1  # Cog
            self.ship.set_world_location(self.room1)
        self.ship.db_location = self.bank
        self.ship.save(update_fields=["db_location"])

    def test_balance_shows_ship_by_default(self):
        """Ships are now shown in the default balance listing."""
        result = self.call(CmdBalance(), "")
        self.assertIn("The Grey Widow", result)

    def test_balance_shows_ships_section_heading(self):
        """Ships render under the |wShips:|n subsection."""
        result = self.call(CmdBalance(), "")
        self.assertIn("Ships", result)

    def test_balance_uses_get_owned_display_for_berth(self):
        """The ship's berth location should appear via get_owned_display()."""
        result = self.call(CmdBalance(), "")
        # ShipNFTItem.get_owned_display includes 'berthed at <room name>'
        self.assertIn("berthed at", result)
        self.assertIn(self.room1.key, result)

    def test_balance_does_not_show_cannot_be_withdrawn_label(self):
        """The old 'cannot be withdrawn' wording should be gone."""
        result = self.call(CmdBalance(), "")
        self.assertNotIn("cannot be withdrawn", result)

    def test_balance_does_not_hint_at_balance_all(self):
        """The 'use balance all to see' hint is gone — ships show by default."""
        result = self.call(CmdBalance(), "")
        self.assertNotIn("balance all", result)


class TestCmdBalanceHidesPets(EvenniaCommandTest):
    """
    Pets are managed from stable rooms, not bank rooms. They live in
    account_bank.contents while stabled but must NEVER show in `balance`.

    This guards the BaseNFTItem filter — if anyone widens it later, this
    test fails loudly.
    """

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

    def test_balance_hides_stabled_pet(self):
        """A pet object in bank.contents should not appear in `balance`."""
        from unittest.mock import MagicMock
        # Use a lightweight stand-in rather than a full BasePet — the
        # filter check is `isinstance(obj, BaseNFTItem)`, so anything not
        # inheriting BaseNFTItem is invisible. A MagicMock with is_pet=True
        # exercises the contract without spinning up actor machinery.
        fake_pet = MagicMock()
        fake_pet.is_pet = True
        fake_pet.key = "Fluffy"
        # Inject directly into bank.contents via the underlying queryset is
        # tricky; instead, monkeypatch bank.contents to include our fake.
        original_contents = list(self.bank.contents)
        type(self.bank).contents = property(
            lambda s: original_contents + [fake_pet]
        )
        try:
            result = self.call(CmdBalance(), "")
        finally:
            del type(self.bank).contents
        self.assertNotIn("Fluffy", result)


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
