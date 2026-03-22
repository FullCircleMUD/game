"""
Tests for CmdQuitIC — combat blocking.
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_quit_ic import CmdQuitIC


class TestCmdQuitIC(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_quit_blocked_in_combat(self):
        """Quit is refused when character has a combat_handler script."""
        with patch.object(
            self.char1.scripts, "get", return_value=[MagicMock()]
        ):
            self.call(
                CmdQuitIC(), "",
                "You can't quit while in combat! You must flee or end the fight first.",
            )

    def test_quit_allowed_out_of_combat(self):
        """Quit works normally when not in combat."""
        with patch.object(
            self.char1.scripts, "get", return_value=[]
        ):
            # Should not show the combat blocked message
            result = self.call(CmdQuitIC(), "", "")
            self.assertNotIn("combat", result.lower() if result else "")
