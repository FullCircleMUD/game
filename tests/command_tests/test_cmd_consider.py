"""
Tests for CmdConsider — gauge target difficulty by multi-stat comparison.

evennia test --settings settings tests.command_tests.test_cmd_consider
"""

from evennia.utils.test_resources import EvenniaCommandTest
from evennia.utils import create

from commands.all_char_cmds.cmd_consider import CmdConsider, _compare, _compare_armor


class TestCmdConsider(EvenniaCommandTest):
    """Test the consider command."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True

    def test_no_args(self):
        """No args shows error."""
        result = self.call(CmdConsider(), "", caller=self.char1)
        self.assertIn("Consider who?", result)

    def test_target_not_found(self):
        """Invalid target name shows search failure."""
        result = self.call(CmdConsider(), "nonexistent", caller=self.char1)
        self.assertIn("no 'nonexistent' here", result.lower())

    def test_same_stats_shows_about_the_same(self):
        """Equal stats should produce 'About the same' assessments."""
        result = self.call(CmdConsider(), "Char2", caller=self.char1)
        self.assertIn("About the same", result)

    def test_output_has_all_dimensions(self):
        """Output should show level, health, armor, attacks, damage."""
        result = self.call(CmdConsider(), "Char2", caller=self.char1)
        self.assertIn("level", result.lower())
        self.assertIn("health", result.lower())
        self.assertIn("armor", result.lower())
        self.assertIn("attacks", result.lower())
        self.assertIn("damage", result.lower())

    def test_non_actor(self):
        """Considering a non-actor object — actor_hostile doesn't find it."""
        obj = create.create_object(
            "evennia.objects.objects.DefaultObject",
            key="rock",
            location=self.room1,
        )
        result = self.call(CmdConsider(), "rock", caller=self.char1)
        # actor_hostile only finds actors — rock is not found
        self.assertIn("no 'rock' here", result.lower())
        obj.delete()


class TestCompareFunction(EvenniaCommandTest):
    """Test the _compare helper function directly."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_equal_values(self):
        msg = _compare(10, 10)
        self.assertIn("About the same", msg)

    def test_both_zero(self):
        msg = _compare(0, 0)
        self.assertIn("About the same", msg)

    def test_theirs_much_higher(self):
        msg = _compare(5, 20)
        self.assertIn("Much higher", msg)

    def test_theirs_much_lower(self):
        msg = _compare(20, 5)
        self.assertIn("Much lower", msg)

    def test_theirs_slightly_higher(self):
        msg = _compare(10, 12)
        self.assertIn("Slightly higher", msg)

    def test_theirs_slightly_lower(self):
        msg = _compare(10, 8)
        self.assertIn("Slightly lower", msg)


class TestCompareArmorFunction(EvenniaCommandTest):
    """Test the _compare_armor helper function."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def test_same_ac(self):
        msg = _compare_armor(10, 10)
        self.assertIn("About the same", msg)

    def test_much_better_armored(self):
        """Lower AC = better armor. their_ac much lower than yours."""
        msg = _compare_armor(18, 10)
        self.assertIn("Much better armored", msg)

    def test_much_worse_armored(self):
        msg = _compare_armor(10, 18)
        self.assertIn("Much worse armored", msg)
