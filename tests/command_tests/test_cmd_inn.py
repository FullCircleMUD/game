"""
Tests for inn commands — stew, ale, and menu.

Stew tests use the static fallback path (superuser/vault wallet) since
the AMM path requires deferToThread which doesn't work synchronously
in tests. The AMM integration is tested via the shopkeeper test suite.

evennia test --settings settings tests.command_tests.test_cmd_inn
"""

from unittest.mock import patch

from django.conf import settings
from evennia.utils.test_resources import EvenniaCommandTest

from enums.hunger_level import HungerLevel
from enums.thirst_level import ThirstLevel
from commands.room_specific_cmds.inn.cmd_stew import CmdStew, FALLBACK_PRICE
from commands.room_specific_cmds.inn.cmd_ale import CmdAle
from commands.room_specific_cmds.inn.cmd_menu import CmdMenu


class TestCmdStew(EvenniaCommandTest):
    """Test buying and eating stew (static fallback path)."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # Use vault address so stew hits the static fallback path
        self.account.attributes.add(
            "wallet_address", settings.XRPL_VAULT_ADDRESS
        )
        self.char1.db.gold = 100
        self.char1.db.resources = {}
        self.char1.hunger_level = HungerLevel.HUNGRY

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_success(self, mock_sink):
        """Stew should spend gold and increment hunger."""
        self.call(CmdStew(), "")
        self.assertEqual(self.char1.get_gold(), 100 - FALLBACK_PRICE)
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_hunger_message(self, mock_sink):
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
        self.assertEqual(self.char1.get_gold(), 100)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_to_full_sets_free_pass(self, mock_sink):
        """Eating stew to FULL should set hunger_free_pass_tick."""
        self.char1.hunger_level = HungerLevel.SATISFIED
        self.char1.hunger_free_pass_tick = False
        self.call(CmdStew(), "")
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)
        self.assertTrue(self.char1.hunger_free_pass_tick)

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_stew_not_full_no_free_pass(self, mock_sink):
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
        self.account.attributes.add(
            "wallet_address", settings.XRPL_VAULT_ADDRESS
        )
        self.char1.db.gold = 10
        self.char1.db.resources = {}
        # Default thirst is REFRESHED, which the ale command blocks on
        # with "You are not thirsty." Drop it so the purchase path runs.
        self.char1.thirst_level = ThirstLevel.THIRSTY

    @patch("blockchain.xrpl.services.gold.GoldService.sink")
    def test_ale_success(self, mock_sink):
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
    def test_ale_no_hunger_effect(self, mock_sink):
        """Ale should not change hunger level."""
        self.char1.hunger_level = HungerLevel.HUNGRY
        self.call(CmdAle(), "")
        self.assertEqual(self.char1.hunger_level, HungerLevel.HUNGRY)


class TestCmdMenu(EvenniaCommandTest):
    """Test the menu display."""

    def create_script(self):
        pass

    def test_menu_shows_items(self):
        """Menu should list stew and ale with prices."""
        result = self.call(CmdMenu(), "")
        self.assertIn("stew", result)
        self.assertIn("ale", result)
        self.assertIn("gold", result)
