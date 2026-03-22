"""
Tests for CmdConsider — gauge target difficulty by level comparison.

evennia test --settings settings tests.command_tests.test_cmd_consider
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_consider import CmdConsider, _get_consider_message


class TestCmdConsider(EvenniaCommandTest):
    """Test the consider command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.total_level = 10
        self.char2.total_level = 10

    def test_no_args(self):
        """No args shows error."""
        result = self.call(CmdConsider(), "", caller=self.char1)
        self.assertIn("Consider who?", result)

    def test_target_not_found(self):
        """Invalid target name shows search failure."""
        result = self.call(CmdConsider(), "nonexistent", caller=self.char1)
        self.assertIn("Could not find", result)

    def test_equal_level(self):
        """Same level shows 'perfect match'."""
        result = self.call(CmdConsider(), "Char2", caller=self.char1)
        self.assertIn("perfect match", result.lower())

    def test_easy_target(self):
        """Much lower level target shows easy message."""
        self.char2.total_level = 1
        result = self.call(CmdConsider(), "Char2", caller=self.char1)
        self.assertIn("needle", result.lower())

    def test_chicken(self):
        """Massively lower level target shows chicken message."""
        self.char2.total_level = 1
        self.char1.total_level = 20
        result = self.call(CmdConsider(), "Char2", caller=self.char1)
        self.assertIn("chicken", result.lower())

    def test_hard_target(self):
        """Higher level target shows difficulty message."""
        self.char2.total_level = 15
        self.char1.total_level = 10
        result = self.call(CmdConsider(), "Char2", caller=self.char1)
        self.assertIn("lucky, punk", result.lower())

    def test_mad_target(self):
        """Massively higher level shows 'mad' message."""
        self.char2.total_level = 25
        self.char1.total_level = 10
        result = self.call(CmdConsider(), "Char2", caller=self.char1)
        self.assertIn("mad", result.lower())

    def test_non_actor(self):
        """Considering a non-actor object shows error."""
        obj = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="rock",
            location=self.room1,
        )
        result = self.call(CmdConsider(), "rock", caller=self.char1)
        self.assertIn("can't consider", result.lower())
        obj.delete()


class TestConsiderMessages(EvenniaCommandTest):
    """Test the graduated message function directly."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_all_tiers(self):
        """Each level diff tier returns a distinct message."""
        cases = [
            (-15, "chicken"),
            (-7, "needle"),
            (-3, "Easy"),
            (-1, "Fairly easy"),
            (0, "perfect match"),
            (1, "some luck"),
            (2, "lot of luck"),
            (3, "great equipment"),
            (5, "lucky, punk"),
            (8, "mad!?"),
            (15, "ARE mad"),
        ]
        for diff, expected_fragment in cases:
            msg = _get_consider_message(diff)
            self.assertIn(
                expected_fragment, msg,
                f"diff={diff}: expected '{expected_fragment}' in '{msg}'",
            )
