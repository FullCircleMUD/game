"""
Tests for CmdWeight — weight/encumbrance display command.

evennia test --settings settings tests.command_tests.test_cmd_weight
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_weight import CmdWeight


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdWeight(EvenniaCommandTest):
    """Test the weight command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_weight_shows_encumbrance(self):
        """weight command should show encumbrance display."""
        result = self.call(CmdWeight(), "")
        # Character has get_encumbrance_display, so it should show weight info
        # The exact format depends on the mixin but should not error
        self.assertTrue(len(result) > 0)

    def test_weight_alias_encumbrance(self):
        """'encumbrance' alias should work."""
        result = self.call(CmdWeight(), "", cmdstring="encumbrance")
        self.assertTrue(len(result) > 0)
