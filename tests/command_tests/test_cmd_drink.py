"""
Tests for the `drink` command — sip from a water container in inventory.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_drink import CmdDrink
from enums.thirst_level import ThirstLevel


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class CmdDrinkTestBase(EvenniaCommandTest):
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.room1.always_lit = True
        self.char1.thirst_level = ThirstLevel.THIRSTY

    def _make_canteen(self):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            canteen = create.create_object(
                "typeclasses.items.water_containers.canteen_nft_item.CanteenNFTItem",
                key="a leather canteen",
                location=self.char1,
                nohome=True,
            )
            canteen.token_id = 9201
        return canteen


class TestCmdDrinkNoContainer(CmdDrinkTestBase):

    def test_drink_with_nothing_to_drink(self):
        result = self.call(CmdDrink(), "")
        self.assertIn("nothing to drink", result.lower())


class TestCmdDrinkSuccess(CmdDrinkTestBase):

    def test_drink_steps_thirst_up(self):
        self._make_canteen()
        starting = self.char1.thirst_level.value
        self.call(CmdDrink(), "")
        self.assertEqual(self.char1.thirst_level.value, starting + 1)

    def test_drink_named_canteen(self):
        canteen = self._make_canteen()
        self.call(CmdDrink(), "canteen")
        self.assertEqual(canteen.current, canteen.max_capacity - 1)

    def test_drink_emits_room_message(self):
        self._make_canteen()
        # Should not raise — multi-perspective messaging path runs cleanly.
        self.call(CmdDrink(), "")


class TestCmdDrinkEmpty(CmdDrinkTestBase):

    def test_drink_empty_skips_to_next(self):
        empty = self._make_canteen()
        empty.current = 0
        # Only one container, and it's empty — should report nothing to drink
        result = self.call(CmdDrink(), "")
        self.assertIn("nothing to drink", result.lower())
