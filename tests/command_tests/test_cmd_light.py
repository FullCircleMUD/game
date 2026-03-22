"""
Tests for light, extinguish, and refuel commands.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_light import CmdLight, CmdExtinguish
from commands.all_char_cmds.cmd_refuel import CmdRefuel


class TestCmdLight(EvenniaCommandTest):
    """Test the 'light' command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="torch",
            location=self.char1,
            nohome=True,
        )

    def test_light_no_args(self):
        self.call(CmdLight(), "", "Light what?")

    def test_light_nonexistent_item(self):
        result = self.call(CmdLight(), "banana")
        self.assertIn("Could not find", result)

    def test_light_non_light_source(self):
        rock = create.create_object(key="rock", location=self.char1, nohome=True)
        result = self.call(CmdLight(), "rock")
        self.assertIn("not something you can light", result)

    def test_light_torch_success(self):
        self.torch.is_lit = False
        result = self.call(CmdLight(), "torch")
        self.assertIn("light", result.lower())
        self.assertTrue(self.torch.is_lit)

    def test_light_already_lit(self):
        self.torch.is_lit = True
        result = self.call(CmdLight(), "torch")
        self.assertIn("already lit", result)


class TestCmdExtinguish(EvenniaCommandTest):
    """Test the 'extinguish' command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="torch",
            location=self.char1,
            nohome=True,
        )

    def test_extinguish_no_args(self):
        self.call(CmdExtinguish(), "", "Extinguish what?")

    def test_extinguish_lit_torch(self):
        self.torch.is_lit = True
        result = self.call(CmdExtinguish(), "torch")
        self.assertIn("extinguish", result.lower())
        self.assertFalse(self.torch.is_lit)

    def test_extinguish_unlit_torch(self):
        self.torch.is_lit = False
        result = self.call(CmdExtinguish(), "torch")
        self.assertIn("not lit", result)

    def test_extinguish_non_light_source(self):
        rock = create.create_object(key="rock", location=self.char1, nohome=True)
        result = self.call(CmdExtinguish(), "rock")
        self.assertIn("not something you can extinguish", result)


class TestCmdRefuel(EvenniaCommandTest):
    """Test the 'refuel' command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.lantern = create.create_object(
            "typeclasses.items.holdables.lantern_nft_item.LanternNFTItem",
            key="lantern",
            location=self.char1,
            nohome=True,
        )

    def test_refuel_no_args(self):
        self.call(CmdRefuel(), "", "Refuel what?")

    def test_refuel_non_light_source(self):
        rock = create.create_object(key="rock", location=self.char1, nohome=True)
        result = self.call(CmdRefuel(), "rock")
        self.assertIn("not something you can refuel", result)

    def test_refuel_already_full(self):
        result = self.call(CmdRefuel(), "lantern")
        self.assertIn("already full", result)

    def test_refuel_consumable_rejected(self):
        """Can't refuel a torch (single-use)."""
        torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="torch",
            location=self.char1,
            nohome=True,
        )
        torch.fuel_remaining = 10
        result = self.call(CmdRefuel(), "torch")
        self.assertIn("single-use", result)

    def test_refuel_no_wheat(self):
        """Fails when player has no wheat."""
        self.lantern.fuel_remaining = 10
        result = self.call(CmdRefuel(), "lantern")
        self.assertIn("don't have any", result)

    @patch("commands.all_char_cmds.cmd_refuel.FUEL_RESOURCE_ID", 1)
    def test_refuel_success(self):
        """Refueling with wheat works — mock the resource consumption."""
        self.lantern.fuel_remaining = 10

        # Mock get_resource and return_resource_to_sink to avoid blockchain DB
        with patch.object(self.char1, "get_resource", return_value=5), \
             patch.object(self.char1, "return_resource_to_sink") as mock_consume:
            result = self.call(CmdRefuel(), "lantern")
            self.assertIn("refuel", result.lower())
            self.assertEqual(self.lantern.fuel_remaining, self.lantern.max_fuel)
            mock_consume.assert_called_once_with(1, 1)
