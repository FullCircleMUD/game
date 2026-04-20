"""
Tests for the `refill` command — top up a water container at a water source.

evennia test --settings settings tests.command_tests.test_cmd_refill
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_refill import CmdRefill


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdRefill(EvenniaCommandTest):
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.fountain = create.create_object(
            "typeclasses.world_objects.fountain_fixture.FountainFixture",
            key="a stone fountain",
            location=self.room1,
            nohome=True,
        )

    def _make_canteen(self, current=1):
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            canteen = create.create_object(
                "typeclasses.items.water_containers.canteen_nft_item.CanteenNFTItem",
                key="a leather canteen",
                location=self.char1,
                nohome=True,
            )
            canteen.token_id = 9301
            canteen.current = current
        return canteen

    def test_refill_success(self):
        """refill canteen from fountain should fill the canteen."""
        canteen = self._make_canteen(current=1)
        result = self.call(CmdRefill(), "canteen from fountain")
        self.assertIn("refill", result.lower())
        self.assertEqual(canteen.current, canteen.max_capacity)

    def test_refill_already_full(self):
        """refill a full canteen should fail."""
        self._make_canteen(current=5)
        result = self.call(CmdRefill(), "canteen from fountain")
        self.assertIn("already full", result.lower())

    def test_no_args(self):
        """refill with no args should show usage."""
        result = self.call(CmdRefill(), "")
        self.assertIn("Usage", result)

    def test_missing_source(self):
        """refill with only container arg should show usage."""
        self._make_canteen()
        result = self.call(CmdRefill(), "canteen")
        self.assertIn("Usage", result)

    def test_no_fountain_in_room(self):
        """refill with no water source should error."""
        self._make_canteen()
        self.fountain.delete()
        result = self.call(CmdRefill(), "canteen from fountain")
        self.assertIn("don't see", result)

    def test_non_water_source(self):
        """refill from a non-water-source fixture should error."""
        self._make_canteen()
        create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a stone pedestal",
            location=self.room1,
            nohome=True,
        )
        result = self.call(CmdRefill(), "canteen from pedestal")
        self.assertIn("can't refill from", result)

    def test_non_water_container(self):
        """refill a non-water-container item should error."""
        with patch("blockchain.xrpl.services.nft.NFTService.update_metadata"), \
             patch("blockchain.xrpl.services.nft.NFTService.craft_output"):
            sword = create.create_object(
                "typeclasses.items.base_nft_item.BaseNFTItem",
                key="a rusty sword",
                location=self.char1,
                nohome=True,
            )
            sword.token_id = 9302
        result = self.call(CmdRefill(), "sword from fountain")
        self.assertIn("can't refill", result)

    def test_container_not_in_inventory(self):
        """refill a container not in inventory should error."""
        result = self.call(CmdRefill(), "canteen from fountain")
        self.assertIn("don't see", result)

    def test_darkness_blocks(self):
        """refill in darkness should error."""
        self._make_canteen()
        self.room1.always_lit = False
        self.room1.natural_light = False
        result = self.call(CmdRefill(), "canteen from fountain")
        self.assertIn("too dark", result)
