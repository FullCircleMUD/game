"""
Tests for CmdRent — safe logout at an inn.

evennia test --settings settings tests.command_tests.test_cmd_rent
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.room_specific_cmds.inn.cmd_rent import CmdRent


class TestCmdRent(EvenniaCommandTest):

    def create_script(self):
        pass

    def test_rent_blocked_in_combat(self):
        """Rent is refused when character has a combat_handler script."""
        with patch.object(
            self.char1.scripts, "get", return_value=[MagicMock()]
        ):
            self.call(
                CmdRent(), "",
                "You can't rent a room while in combat!",
            )

    def test_rent_shows_safe_message(self):
        """Rent should confirm belongings are safe."""
        with patch.object(
            self.char1.scripts, "get", return_value=[]
        ):
            result = self.call(CmdRent(), "")
            self.assertIn("belongings are safe", result)
