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
        self.room1.always_lit = True
        self.torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="torch",
            location=self.char1,
            nohome=True,
        )
        # Equip the torch — must be held to light
        self.char1.wear(self.torch)

    def test_light_no_args(self):
        self.call(CmdLight(), "", "Light what?")

    def test_light_nonexistent_item(self):
        self.call(CmdLight(), "banana", "You aren't wearing 'banana'.")

    def test_light_non_light_source(self):
        """Non-light-source equipped item can't be lit."""
        from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
        # Remove torch first to free the hold slot
        self.char1.remove(self.torch)
        shield = create.create_object(
            HoldableNFTItem, key="shield", location=self.char1, nohome=True,
        )
        self.char1.wear(shield)
        result = self.call(CmdLight(), "shield")
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

    def test_light_unequipped_not_found(self):
        """An unequipped torch in inventory can't be lit."""
        self.char1.remove(self.torch)
        self.call(CmdLight(), "torch", "You aren't wearing 'torch'.")

    # --- Lighting by touch ---
    #
    # An equipped torch is found by feel, so darkness costs the time
    # spent searching rather than the action.

    def _light_blind(self, args="torch"):
        """Call light while sightless, returning (output, completion)."""
        self.room1.always_lit = False
        self.room1.natural_light = False
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdLight(), args)
        # delay(interval, _tick, step) — the callback is bound to its step
        delayed = mock_delay.call_args[0] if mock_delay.call_args else None
        complete = (lambda: delayed[1](*delayed[2:])) if delayed else None
        return out, complete

    def _finish(self, complete):
        """Run the deferred completion, collecting what the caller hears."""
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        complete()
        return " ".join(said)

    def test_a_search_by_touch_refuses_in_its_own_wording(self):
        """The wiring, not the wording — assert against the constant."""
        from utils.busy import BUSY_MESSAGE, FUMBLE_BUSY_MESSAGE, check_busy

        self.torch.is_lit = False
        self._light_blind()
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        check_busy(self.char1)
        self.assertIn(FUMBLE_BUSY_MESSAGE, said)
        self.assertNotIn(BUSY_MESSAGE, said)

    def test_a_searcher_cannot_walk_off_and_lose_their_bearings(self):
        from utils.busy import BUSY_MOVE_MESSAGE, FUMBLE_MOVE_MESSAGE

        self.torch.is_lit = False
        self._light_blind()
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        self.assertFalse(self.char1.at_pre_move(self.room2))
        self.assertIn(FUMBLE_MOVE_MESSAGE, said)
        self.assertNotIn(BUSY_MOVE_MESSAGE, said)

    def test_lighting_in_the_dark_announces_the_search(self):
        self.torch.is_lit = False
        out, _ = self._light_blind()
        self.assertIn("feel across your gear", out)

    def test_lighting_in_the_dark_succeeds_after_the_search(self):
        self.torch.is_lit = False
        _, complete = self._light_blind()
        complete()
        self.assertTrue(self.torch.is_lit)

    def test_nothing_is_lit_until_the_search_ends(self):
        self.torch.is_lit = False
        self._light_blind()
        self.assertFalse(self.torch.is_lit)

    def test_a_missing_item_is_searched_for_first(self):
        """The search gives nothing away — you grope, then find out."""
        out, complete = self._light_blind("banana")
        self.assertIn("feel across your gear", out)
        self.assertNotIn("aren't wearing", out)
        self.assertIn("aren't wearing 'banana'", self._finish(complete))

    def test_lighting_when_sighted_does_not_search(self):
        self.torch.is_lit = False
        result = self.call(CmdLight(), "torch")
        self.assertNotIn("feel across your gear", result)

    def test_lighting_is_refused_while_busy(self):
        self.char1.ndb.is_processing = True
        self.call(CmdLight(), "torch", "You are busy.")


class TestCmdExtinguish(EvenniaCommandTest):
    """Test the 'extinguish' command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.torch = create.create_object(
            "typeclasses.items.holdables.torch_nft_item.TorchNFTItem",
            key="torch",
            location=self.char1,
            nohome=True,
        )
        # Equip the torch — must be held to extinguish
        self.char1.wear(self.torch)

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
        """Non-light-source equipped item can't be extinguished."""
        from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
        # Remove torch first to free the hold slot
        self.char1.remove(self.torch)
        shield = create.create_object(
            HoldableNFTItem, key="shield", location=self.char1, nohome=True,
        )
        self.char1.wear(shield)
        result = self.call(CmdExtinguish(), "shield")
        self.assertIn("not something you can extinguish", result)


class TestCmdRefuel(EvenniaCommandTest):
    """Test the 'refuel' command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
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

    # --- Refuelling by touch ---
    #
    # The lantern is in your own pack or on your own belt, so darkness
    # costs the time spent finding it rather than the action.

    def _refuel_blind(self, args="lantern"):
        """Call refuel while sightless, returning (output, completion)."""
        self.room1.always_lit = False
        self.room1.natural_light = False
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdRefuel(), args)
        # delay(interval, _tick, step) — the callback is bound to its step
        delayed = mock_delay.call_args[0] if mock_delay.call_args else None
        complete = (lambda: delayed[1](*delayed[2:])) if delayed else None
        return out, complete

    def _finish(self, complete):
        """Run the deferred completion, collecting what the caller hears."""
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        complete()
        return " ".join(said)

    def test_refuelling_in_the_dark_announces_the_fumble(self):
        self.lantern.fuel_remaining = 10
        out, _ = self._refuel_blind()
        self.assertIn("then pour by touch", out)

    @patch("commands.all_char_cmds.cmd_refuel.FUEL_RESOURCE_ID", 1)
    def test_refuelling_in_the_dark_succeeds_after_the_fumble(self):
        self.lantern.fuel_remaining = 10
        with patch.object(self.char1, "get_resource", return_value=5), \
             patch.object(self.char1, "return_resource_to_sink"):
            _, complete = self._refuel_blind()
            complete()
        self.assertEqual(self.lantern.fuel_remaining, self.lantern.max_fuel)

    def test_nothing_is_poured_until_the_fumble_ends(self):
        self.lantern.fuel_remaining = 10
        self._refuel_blind()
        self.assertEqual(self.lantern.fuel_remaining, 10)

    def test_a_missing_item_is_searched_for_first(self):
        """The search gives nothing away — you fumble, then find out."""
        out, complete = self._refuel_blind("banana")
        self.assertIn("then pour by touch", out)
        self.assertNotIn("aren't carrying", out)
        self.assertIn("aren't carrying 'banana'", self._finish(complete))

    def test_refuelling_when_sighted_does_not_fumble(self):
        self.lantern.fuel_remaining = 10
        result = self.call(CmdRefuel(), "lantern")
        self.assertNotIn("fumble", result)

    def test_refuelling_is_refused_while_busy(self):
        self.char1.ndb.is_processing = True
        self.call(CmdRefuel(), "lantern", "You are busy.")
