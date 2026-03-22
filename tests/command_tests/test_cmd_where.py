"""
Tests for the where command.

evennia test --settings settings tests.command_tests.test_cmd_where
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_where import CmdWhere


class TestCmdWhere(EvenniaCommandTest):
    """Test the where command output."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_where_shows_room_name(self):
        """Where should display the current room name."""
        result = self.call(CmdWhere(), "")
        self.assertIn("Room:", result)
        self.assertIn(self.room1.key, result)

    def test_where_shows_district(self):
        """Where should display district when tagged."""
        self.room1.tags.add("market_district", category="district")
        result = self.call(CmdWhere(), "")
        self.assertIn("District:", result)
        self.assertIn("Market District", result)

    def test_where_shows_zone(self):
        """Where should display zone when tagged."""
        self.room1.tags.add("test_economic_zone", category="zone")
        result = self.call(CmdWhere(), "")
        self.assertIn("Zone:", result)
        self.assertIn("Test Economic Zone", result)

    def test_where_shows_unknown_when_untagged(self):
        """Where should show Unknown for missing district/zone."""
        result = self.call(CmdWhere(), "")
        self.assertIn("Unknown", result)

    def test_where_no_location(self):
        """Where should handle character with no location."""
        self.char1.location = None
        result = self.call(CmdWhere(), "")
        self.assertIn("nowhere", result)
