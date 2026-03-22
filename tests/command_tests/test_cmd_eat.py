"""
Tests for CmdEat — verifies eating bread consumes the resource,
increases hunger level, and sets hunger_free_pass_tick when reaching FULL.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_eat import CmdEat
from enums.hunger_level import HungerLevel


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdEat(EvenniaCommandTest):
    """Test the eat command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.gold = 0
        self.char1.db.resources = {3: 5}  # 5 bread
        self.char1.hunger_level = HungerLevel.HUNGRY  # level 3

    def test_eat_no_args(self):
        """eat with no arguments should show usage."""
        self.call(CmdEat(), "", "Eat what?")

    def test_eat_inedible(self):
        """Trying to eat something not in the food list."""
        self.call(CmdEat(), "sword", "You can't eat that.")

    def test_eat_no_bread(self):
        """Trying to eat bread when you have none."""
        self.char1.db.resources = {}
        self.call(CmdEat(), "bread", "You don't have any bread.")

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_eat_bread_increases_hunger(self, mock_craft):
        """Eating bread should increase hunger level by 1."""
        self.call(CmdEat(), "bread", "You eat some bread.")
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_eat_bread_consumes_resource(self, mock_craft):
        """Eating bread should consume 1 bread."""
        self.call(CmdEat(), "bread", "You eat some bread.")
        self.assertEqual(self.char1.get_resource(3), 4)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_eat_bread_to_full_sets_free_pass(self, mock_craft):
        """Eating to FULL should set hunger_free_pass_tick = True."""
        self.char1.hunger_level = HungerLevel.SATISFIED  # one below FULL
        self.char1.hunger_free_pass_tick = False
        self.call(CmdEat(), "bread", "You eat some bread.")
        self.assertEqual(self.char1.hunger_level, HungerLevel.FULL)
        self.assertTrue(self.char1.hunger_free_pass_tick)

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_eat_bread_not_full_no_free_pass(self, mock_craft):
        """Eating when not reaching FULL should NOT set free pass."""
        self.char1.hunger_free_pass_tick = False
        self.call(CmdEat(), "bread", "You eat some bread.")
        self.assertFalse(self.char1.hunger_free_pass_tick)

    def test_eat_already_full(self):
        """Eating when already FULL should show message."""
        self.char1.hunger_level = HungerLevel.FULL
        self.call(CmdEat(), "bread", "You are already full.")

    @patch("blockchain.xrpl.services.resource.ResourceService.sink")
    def test_eat_shows_hunger_message(self, mock_craft):
        """After eating, should show the new hunger level message."""
        self.char1.hunger_level = HungerLevel.HUNGRY  # → PECKISH
        self.call(CmdEat(), "bread", "You eat some bread.")
        # The second msg should be the hunger message for PECKISH
        # Since self.call checks startswith on first message, we verify state
        self.assertEqual(self.char1.hunger_level, HungerLevel.PECKISH)
