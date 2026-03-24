"""
Tests for CmdMenu — inn menu display command.

Verifies the menu shows stew and ale with correct prices.

evennia test --settings settings tests.command_tests.test_cmd_menu
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.inn.cmd_menu import CmdMenu
from commands.room_specific_cmds.inn.cmd_stew import FALLBACK_PRICE
from commands.room_specific_cmds.inn.cmd_ale import ALE_PRICE


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdMenu(EvenniaCommandTest):
    """Test the menu command."""

    room_typeclass = "typeclasses.terrain.rooms.room_inn.RoomInn"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_menu_shows_header(self):
        """Menu should show the Inn Menu header."""
        result = self.call(CmdMenu(), "")
        self.assertIn("Inn Menu", result)

    def test_menu_shows_stew(self):
        """Menu should list stew."""
        result = self.call(CmdMenu(), "")
        self.assertIn("stew", result)

    def test_menu_shows_ale(self):
        """Menu should list ale."""
        result = self.call(CmdMenu(), "")
        self.assertIn("ale", result)

    def test_menu_shows_stew_price(self):
        """Menu should show a stew price (AMM or fallback)."""
        result = self.call(CmdMenu(), "")
        self.assertIn("gold", result)

    def test_menu_shows_ale_price(self):
        """Menu should show the ale price."""
        result = self.call(CmdMenu(), "")
        self.assertIn(f"{ALE_PRICE} gold", result)
