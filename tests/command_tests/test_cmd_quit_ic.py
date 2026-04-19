"""
Tests for CmdQuitIC — combat blocking, gear drop, and confirmation.

evennia test --settings settings tests.command_tests.test_cmd_quit_ic
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_quit_ic import CmdQuitIC
from typeclasses.world_objects.quit_drop import QuitDrop


class TestCmdQuitIC(EvenniaCommandTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_quit_blocked_in_combat(self):
        """Quit is refused when character has a combat_handler script."""
        with patch.object(
            self.char1.scripts, "get", return_value=[MagicMock()]
        ):
            self.call(
                CmdQuitIC(), "",
                "You can't quit while in combat!",
            )

    def test_quit_cancelled_on_no(self):
        """Quit is cancelled when player answers no."""
        with patch.object(
            self.char1.scripts, "get", return_value=[]
        ):
            result = self.call(CmdQuitIC(), "", inputs=["n"])
            self.assertIn("Quit cancelled", result)

    @patch("commands.all_char_cmds.cmd_quit_ic.CmdQuitIC._send_home")
    def test_quit_creates_quit_drop(self, mock_send_home):
        """Quit with confirmation should create a QuitDrop in the room."""
        # Give character gold via db attribute (bypasses service layer)
        self.char1.db.gold = 50

        with patch.object(
            self.char1.scripts, "get", return_value=[]
        ), patch.object(
            self.char1, "transfer_gold_to"
        ):
            self.call(CmdQuitIC(), "", inputs=["y"])

        quit_drops = [
            obj for obj in self.room1.contents
            if isinstance(obj, QuitDrop)
        ]
        self.assertEqual(len(quit_drops), 1)
        self.assertEqual(quit_drops[0].owner_character_key, self.char1.key)
        self.assertEqual(
            quit_drops[0].get_display_name(),
            f"{self.char1.key}'s abandoned pack",
        )

    @patch("commands.all_char_cmds.cmd_quit_ic.CmdQuitIC._send_home")
    def test_quit_no_drop_when_empty(self, mock_send_home):
        """Quit should not create a QuitDrop if character has nothing."""
        self.char1.db.gold = 0
        self.char1.db.resources = {}
        # Clear any contents
        for obj in list(self.char1.contents):
            obj.delete()

        with patch.object(
            self.char1.scripts, "get", return_value=[]
        ):
            self.call(CmdQuitIC(), "", inputs=["y"])

        quit_drops = [
            obj for obj in self.room1.contents
            if isinstance(obj, QuitDrop)
        ]
        self.assertEqual(len(quit_drops), 0)
