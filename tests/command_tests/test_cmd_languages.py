"""
Tests for CmdLanguages — verifies the languages command displays
the character's known languages.

evennia test --settings settings tests.command_tests.test_cmd_languages
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_languages import CmdLanguages


class TestCmdLanguages(EvenniaCommandTest):
    """Test the languages command displays correct output."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_single_language(self):
        """Character with one language should see it listed."""
        self.char1.db.languages = {"common"}
        self.call(CmdLanguages(), "", "You speak: Common.")

    def test_multiple_languages(self):
        """Multiple languages should be sorted and comma-separated."""
        self.char1.db.languages = {"common", "dwarven", "elfish"}
        self.call(CmdLanguages(), "", "You speak: Common, Dwarven, Elfish.")

    def test_no_languages(self):
        """Character with no languages should see a message."""
        self.char1.db.languages = set()
        self.call(CmdLanguages(), "", "You don't speak any languages.")

    def test_none_languages(self):
        """Character with languages not set should see a message."""
        self.char1.db.languages = None
        self.call(CmdLanguages(), "", "You don't speak any languages.")

    def test_all_languages(self):
        """Character with all languages should see them all sorted."""
        self.char1.db.languages = {
            "common", "dwarven", "elfish", "halfling",
            "kobold", "goblin", "dragon", "celestial",
        }
        self.call(
            CmdLanguages(), "",
            "You speak: Celestial, Common, Dragon, Dwarven, Elfish, Goblin, Halfling, Kobold.",
        )
