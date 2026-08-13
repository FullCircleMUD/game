"""
Tests for the `drink` command — sip from a water container in inventory.
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_drink import CmdDrink
from enums.condition import Condition
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


class TestCmdDrinkAtRefreshed(CmdDrinkTestBase):
    """Mirror of `eat`'s 'already full' refusal: drink at REFRESHED should
    refuse with a message and NOT consume a drink from the container."""

    def test_drink_at_refreshed_refuses(self):
        canteen = self._make_canteen()
        self.char1.thirst_level = ThirstLevel.REFRESHED
        starting_current = canteen.current
        result = self.call(CmdDrink(), "")
        self.assertIn("not thirsty", result.lower())
        self.assertEqual(canteen.current, starting_current)
        self.assertEqual(self.char1.thirst_level, ThirstLevel.REFRESHED)

    def test_drink_named_canteen_at_refreshed_refuses(self):
        canteen = self._make_canteen()
        self.char1.thirst_level = ThirstLevel.REFRESHED
        starting_current = canteen.current
        result = self.call(CmdDrink(), "canteen")
        self.assertIn("not thirsty", result.lower())
        self.assertEqual(canteen.current, starting_current)


class TestCmdDrinkSightless(CmdDrinkTestBase):
    """
    Your own pack is found by touch, so darkness and blindness slow the
    drink down rather than preventing it.
    """

    def _darken(self):
        # has_natural_light is a read-only property derived from this.
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _drink_blind(self, args=""):
        """Call drink while sightless, returning (output, completion)."""
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdDrink(), args)
        complete = mock_delay.call_args[0][1] if mock_delay.call_args else None
        return out, complete

    def test_a_dark_room_no_longer_blocks_the_drink(self):
        self._make_canteen()
        self._darken()
        starting = self.char1.thirst_level.value
        _, complete = self._drink_blind()
        complete()
        self.assertEqual(self.char1.thirst_level.value, starting + 1)

    def test_a_blinded_character_still_drinks(self):
        self._make_canteen()
        self.char1.add_condition(Condition.BLINDED)
        starting = self.char1.thirst_level.value
        _, complete = self._drink_blind()
        complete()
        self.assertEqual(self.char1.thirst_level.value, starting + 1)

    def test_the_dark_adds_fumbling_flavour(self):
        self._make_canteen()
        self._darken()
        out, _ = self._drink_blind()
        self.assertIn("fumble blindly", out)

    def test_nothing_is_drunk_until_the_fumble_ends(self):
        self._make_canteen()
        self._darken()
        starting = self.char1.thirst_level.value
        self._drink_blind()
        self.assertEqual(self.char1.thirst_level.value, starting)

    def test_an_empty_pack_is_searched_before_the_refusal(self):
        """The search gives nothing away — you fumble, then find out."""
        self._darken()
        out, complete = self._drink_blind()
        self.assertIn("fumble blindly", out)
        self.assertNotIn("nothing to drink", out)
        complete()

    def test_a_sighted_drinker_gets_no_fumbling(self):
        self._make_canteen()
        result = self.call(CmdDrink(), "")
        self.assertNotIn("fumble", result)

    def test_naming_the_container_still_works_unseen(self):
        canteen = self._make_canteen()
        self._darken()
        _, complete = self._drink_blind("canteen")
        complete()
        self.assertEqual(canteen.current, canteen.max_capacity - 1)

    def test_darkvision_drinks_without_fumbling(self):
        self._make_canteen()
        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdDrink(), "")
        self.assertNotIn("fumble", result)

    def test_drinking_is_refused_while_busy(self):
        self._make_canteen()
        self.char1.ndb.is_processing = True
        self.call(CmdDrink(), "", "You are busy.")
