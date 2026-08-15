"""
Tests for CmdSearch — searching for hidden objects.

evennia test --settings settings tests.command_tests.test_cmd_search
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_search import CmdSearch


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdSearch(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)

    def _make_hidden_fixture(self, find_dc=10):
        obj = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="hidden chest",
            location=self.room1,
            nohome=True,
        )
        obj.is_hidden = True
        obj.find_dc = find_dc
        return obj

    def test_search_nothing_hidden(self):
        self.call(CmdSearch(), "", "You search but find nothing unusual.")

    @patch("utils.dice_roller.randint", return_value=20)
    def test_search_finds_hidden_object(self, mock_roll):
        self._make_hidden_fixture(find_dc=5)
        # discover() broadcasts room msg first, so startswith matches that
        self.call(CmdSearch(), "", "Char discovers something hidden")

    @patch("utils.dice_roller.randint", return_value=1)
    def test_search_fails_high_dc(self, mock_roll):
        self._make_hidden_fixture(find_dc=30)
        self.call(CmdSearch(), "", "You search but find nothing unusual.")

    @patch("utils.dice_roller.randint", return_value=15)
    def test_search_discovers_object(self, mock_roll):
        obj = self._make_hidden_fixture(find_dc=5)
        self.call(CmdSearch(), "", "Char discovers something hidden")
        self.assertFalse(obj.is_hidden)
        self.assertIn(self.char1.key, obj.discovered_by)

    def test_search_already_discovered_not_shown(self):
        """Once discovered, object is no longer hidden — search finds nothing."""
        obj = self._make_hidden_fixture(find_dc=5)
        obj.discover(self.char1)
        self.call(CmdSearch(), "", "You search but find nothing unusual.")


class TestCmdSearchSightless(EvenniaCommandTest):
    """Searching without sight is slow and harder, not impossible."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _search_blind(self):
        """Search sightless, returning (output, deferred completion)."""
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdSearch(), "")
        # delay(interval, _tick, step) — the callback is bound to its step
        delayed = mock_delay.call_args[0] if mock_delay.call_args else None
        complete = (lambda: delayed[1](*delayed[2:])) if delayed else None
        return out, complete

    def test_a_dark_room_searches_by_touch(self):
        self._darken()
        out, _ = self._search_blind()
        self.assertIn("searching by touch", out)

    def test_a_blinded_searcher_fumbles_in_a_lit_room(self):
        """is_dark alone never asked this — a blind character searched fine."""
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)
        out, _ = self._search_blind()
        self.assertIn("searching by touch", out)

    def test_a_blinded_searcher_fumbles_even_with_darkvision(self):
        """Darkvision is night vision, not a cure for blindness."""
        from enums.condition import Condition

        self.char1.add_condition(Condition.DARKVISION)
        self.char1.add_condition(Condition.BLINDED)
        out, _ = self._search_blind()
        self.assertIn("searching by touch", out)

    def test_darkvision_searches_normally_in_the_dark(self):
        from enums.condition import Condition

        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdSearch(), "")
        self.assertNotIn("by touch", result)

    def test_a_sighted_searcher_in_a_lit_room_does_not_fumble(self):
        result = self.call(CmdSearch(), "")
        self.assertNotIn("by touch", result)

    def test_the_outcome_waits_for_the_fumble(self):
        self._darken()
        out, _ = self._search_blind()
        self.assertNotIn("nothing unusual", out)

    def test_the_search_resolves_once_the_fumble_ends(self):
        self._darken()
        said = []
        _, complete = self._search_blind()
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        complete()
        self.assertIn("nothing unusual", " ".join(said))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
           return_value=20)
    def test_a_blind_search_rolls_at_disadvantage(self, mock_roll):
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)
        obj = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="hidden chest",
            location=self.room1,
            nohome=True,
        )
        obj.is_hidden = True
        obj.find_dc = 10

        _, complete = self._search_blind()
        complete()
        self.assertTrue(mock_roll.call_args.kwargs.get("disadvantage"))

    @patch("utils.dice_roller.DiceRoller.roll_with_advantage_or_disadvantage",
           return_value=20)
    def test_a_sighted_search_does_not(self, mock_roll):
        obj = create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="hidden chest",
            location=self.room1,
            nohome=True,
        )
        obj.is_hidden = True
        obj.find_dc = 10

        self.call(CmdSearch(), "")
        self.assertFalse(mock_roll.call_args.kwargs.get("disadvantage"))
