"""
Tests for inn commands — stew, ale, and menu.

evennia test --settings settings tests.command_tests.test_cmd_inn
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from enums.hunger_level import HungerLevel
from commands.room_specific_cmds.inn.cmd_stew import CmdStew
from commands.room_specific_cmds.inn.cmd_ale import CmdAle
from commands.room_specific_cmds.inn.cmd_menu import CmdMenu


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdStew(EvenniaCommandTest):
    """Test buying and eating stew."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 10
        self.char1.db.resources = {}
        self.char1.hunger_level = HungerLevel.HUNGRY

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_success(self, mock_craft):
        """Stew should spend 1 gold and increment hunger."""
        self.call(CmdStew(), "")
        self.assertEqual(self.char1.get_gold(), 9)
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_hunger_message(self, mock_craft):
        """Stew should return a message about eating."""
        result = self.call(CmdStew(), "")
        self.assertIn("warm bowl of stew", result)

    def test_stew_no_gold(self):
        """Stew with no gold should be refused."""
        self.char1.db.gold = 0
        result = self.call(CmdStew(), "")
        self.assertIn("can't afford", result)
        self.assertEqual(self.char1.hunger_level, HungerLevel.HUNGRY)

    def test_stew_already_full(self):
        """Stew when already full should be refused."""
        self.char1.hunger_level = HungerLevel.FULL
        result = self.call(CmdStew(), "")
        self.assertIn("already full", result)
        self.assertEqual(self.char1.get_gold(), 10)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_to_full_sets_free_pass(self, mock_craft):
        """Eating stew to FULL should set hunger_free_pass_tick."""
        self.char1.hunger_level = HungerLevel.SATISFIED
        self.char1.hunger_free_pass_tick = False
        self.call(CmdStew(), "")
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)
        self.assertTrue(self.char1.hunger_free_pass_tick)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_not_full_no_free_pass(self, mock_craft):
        """Eating stew but not reaching FULL should not set free pass."""
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.char1.hunger_free_pass_tick = False
        self.call(CmdStew(), "")
        self.assertFalse(self.char1.hunger_free_pass_tick)


class TestCmdAle(EvenniaCommandTest):
    """Test buying and drinking ale."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 10
        self.char1.db.resources = {}

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_ale_success(self, mock_craft):
        """Ale should spend 1 gold and return a message."""
        result = self.call(CmdAle(), "")
        self.assertEqual(self.char1.get_gold(), 9)
        self.assertIn("frothy mug of ale", result)

    def test_ale_no_gold(self):
        """Ale with no gold should be refused."""
        self.char1.db.gold = 0
        result = self.call(CmdAle(), "")
        self.assertIn("can't afford", result)
        self.assertEqual(self.char1.get_gold(), 0)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_ale_no_hunger_effect(self, mock_craft):
        """Ale should not change hunger level."""
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.call(CmdAle(), "")
        self.assertEqual(self.char1.hunger_level, HungerLevel.HUNGRY)


class TestCmdMenu(EvenniaCommandTest):
    """Test the menu display."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()

    def test_menu_shows_items(self):
        """Menu should list stew and ale with prices."""
        result = self.call(CmdMenu(), "")
        self.assertIn("stew", result)
        self.assertIn("ale", result)
        self.assertIn("gold", result)

    def test_menu_shows_prices(self):
        """Menu should show the current prices."""
        result = self.call(CmdMenu(), "")
        self.assertIn("1", result)
