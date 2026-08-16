"""
Tests for CmdSwitch — pull/push/turn/flip switchable fixtures.

evennia test --settings settings tests.command_tests.test_cmd_switch
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_switch import CmdSwitch


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdSwitch(EvenniaCommandTest):
    """Test pull/push command on switch fixtures."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.account.attributes.add("wallet_address", WALLET_A)
        self.lever = create.create_object(
            "typeclasses.world_objects.switch_fixture.SwitchFixture",
            key="a rusty lever",
            location=self.room1,
        )
        self.lever.switch_verb = "pull"
        self.lever.switch_name = "lever"

    def test_pull_activates(self):
        """pull lever should activate it."""
        result = self.call(CmdSwitch(), "lever")
        self.assertIn("pull the lever", result)
        self.assertTrue(self.lever.is_activated)

    def test_pull_again_deactivates(self):
        """pull lever twice should toggle back."""
        self.call(CmdSwitch(), "lever")
        result = self.call(CmdSwitch(), "lever")
        self.assertIn("back", result)
        self.assertFalse(self.lever.is_activated)

    def test_no_target(self):
        """pull with no args should error."""
        result = self.call(CmdSwitch(), "")
        self.assertIn("Pull what", result)

    def test_nonexistent_target(self):
        """pull banana should error."""
        result = self.call(CmdSwitch(), "banana")
        self.assertIn("don't see", result)

    def test_non_switch_target(self):
        """pull on a non-switch object should error."""
        create.create_object(
            "typeclasses.world_objects.base_fixture.WorldFixture",
            key="a stone pedestal",
            location=self.room1,
            nohome=True,
        )
        result = self.call(CmdSwitch(), "pedestal")
        self.assertIn("can't do that", result)

    def test_nothing_switchable(self):
        """pull in room with no switches should error."""
        self.lever.delete()
        result = self.call(CmdSwitch(), "lever")
        self.assertIn("don't see", result)

    # --- Finding a lever by touch ---
    #
    # A lever is found by running your hands along the wall, so darkness
    # costs the time spent hunting rather than the action.

    def _darken(self):
        self.room1.always_lit = False
        self.room1.natural_light = False

    def _pull_blind(self, args="lever"):
        """Call pull while sightless, returning (output, completion)."""
        self._darken()
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdSwitch(), args)
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

    def test_pulling_in_the_dark_announces_the_search(self):
        out, _ = self._pull_blind()
        self.assertIn("hunting for something to pull", out)

    def test_pulling_in_the_dark_succeeds_after_the_search(self):
        _, complete = self._pull_blind()
        complete()
        self.assertTrue(self.lever.is_activated)

    def test_nothing_is_pulled_until_the_search_ends(self):
        self._pull_blind()
        self.assertFalse(self.lever.is_activated)

    def test_a_bare_wall_is_searched_first(self):
        """The search gives nothing away — you grope, then find out."""
        self.lever.delete()
        out, complete = self._pull_blind()
        self.assertIn("hunting for something to pull", out)
        self.assertNotIn("don't see", out)
        self.assertIn("don't see", self._finish(complete))

    def test_a_blinded_character_searches_too(self):
        from enums.condition import Condition

        self.char1.add_condition(Condition.BLINDED)
        with patch("utils.busy.delay") as mock_delay:
            out = self.call(CmdSwitch(), "lever")
        self.assertIn("hunting for something to pull", out)
        self.assertTrue(mock_delay.called)

    def test_darkvision_pulls_normally(self):
        from enums.condition import Condition

        self._darken()
        self.char1.add_condition(Condition.DARKVISION)
        result = self.call(CmdSwitch(), "lever")
        self.assertNotIn("hunting for something", result)
        self.assertTrue(self.lever.is_activated)

    def test_pulling_when_sighted_does_not_search(self):
        result = self.call(CmdSwitch(), "lever")
        self.assertNotIn("hunting for something", result)

    def test_pulling_is_refused_while_busy(self):
        self.char1.ndb.is_processing = True
        self.call(CmdSwitch(), "lever", "You are busy.")
