"""
Tests for CmdSwitch — pull/push/turn/flip switchable fixtures.

evennia test --settings settings tests.command_tests.test_cmd_switch
"""

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
        result = self.call(CmdSwitch(), "Char")
        self.assertIn("can't do that", result)

    def test_nothing_switchable(self):
        """pull in room with no switches should error."""
        self.lever.delete()
        result = self.call(CmdSwitch(), "lever")
        self.assertIn("nothing here", result)
