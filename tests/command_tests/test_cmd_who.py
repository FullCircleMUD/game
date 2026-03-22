"""
Tests for the enhanced who command.

evennia test --settings settings tests.command_tests.test_cmd_who
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.account_cmds.cmdset_account_custom import CmdWho


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdWho(EvenniaCommandTest):
    """Test the enhanced who command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)

    def test_shows_header(self):
        """Who output includes Players Online header."""
        result = self.call(CmdWho(), "", caller=self.account)
        self.assertIn("Players Online", result)

    def test_shows_player_count(self):
        """Who output includes player count."""
        result = self.call(CmdWho(), "", caller=self.account)
        self.assertIn("online", result)

    def test_shows_column_headers(self):
        """Who output includes Name, Lvl, Class, Race columns."""
        result = self.call(CmdWho(), "", caller=self.account)
        self.assertIn("Name", result)
        self.assertIn("Lvl", result)
        self.assertIn("Class", result)
        self.assertIn("Race", result)

    def test_shows_idle_column(self):
        """Who output includes Idle column."""
        result = self.call(CmdWho(), "", caller=self.account)
        self.assertIn("Idle", result)

    def test_admin_shows_location(self):
        """Admin who output includes Location column."""
        result = self.call(CmdWho(), "", caller=self.account)
        self.assertIn("Location", result)
