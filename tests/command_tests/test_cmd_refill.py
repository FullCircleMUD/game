"""
Tests for the `refill` command — top up a water container at a fountain.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_refill import CmdRefill


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class CmdRefillTestBase(EvenniaCommandTest):
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

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

    def _place_fountain(self):
        return create.create_object(
            "typeclasses.world_objects.fountain_fixture.FountainFixture",
            key="a stone fountain",
            location=self.char1.location,
            nohome=True,
        )


class TestRefillNoFountain(CmdRefillTestBase):

    def test_refill_without_fountain_in_room(self):
        self._make_canteen()
        result = self.call(CmdRefill(), "canteen")
        self.assertIn("no water source", result.lower())


class TestRefillSuccess(CmdRefillTestBase):

    def test_refill_at_fountain(self):
        self._place_fountain()
        canteen = self._make_canteen(current=1)
        self.call(CmdRefill(), "canteen")
        self.assertEqual(canteen.current, canteen.max_capacity)

    def test_refill_default_picks_first_non_full(self):
        self._place_fountain()
        canteen = self._make_canteen(current=2)
        self.call(CmdRefill(), "")
        self.assertEqual(canteen.current, canteen.max_capacity)


class TestRefillAlreadyFull(CmdRefillTestBase):

    def test_refill_full_canteen_fails(self):
        self._place_fountain()
        canteen = self._make_canteen(current=5)
        result = self.call(CmdRefill(), "canteen")
        self.assertIn("already full", result.lower())
