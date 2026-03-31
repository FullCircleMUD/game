"""
Tests for CmdGo — 'go <direction>' redirects to the bare direction command.
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_go import CmdGo


class TestCmdGo(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_go_no_args(self):
        """'go' with no direction should show usage hint."""
        result = self.call(CmdGo(), "")
        self.assertIn("Go where?", result)
