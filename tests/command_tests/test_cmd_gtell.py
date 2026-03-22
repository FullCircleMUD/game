"""
Tests for the gtell (group tell) command.

evennia test --settings settings tests.command_tests.test_cmd_gtell
"""

from unittest.mock import MagicMock

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_gtell import CmdGtell


class TestGtellNoGroup(EvenniaCommandTest):
    """Test gtell when not in a group."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.char1.following = None
        self.char2.following = None

    def test_no_args_shows_prompt(self):
        """gtell with no args asks what to say."""
        result = self.call(CmdGtell(), "")
        self.assertIn("Tell your group what?", result)

    def test_not_in_group_talks_to_self(self):
        """gtell without a group sends self-talk message."""
        result = self.call(CmdGtell(), "hello there")
        self.assertIn("You tell yourself", result)
        self.assertIn("hello there", result)

    def test_not_in_group_room_sees_mutter(self):
        """Room sees the character muttering to themselves."""
        self.char2.msg = MagicMock()
        self.call(CmdGtell(), "hello there")
        calls = [str(c) for c in self.char2.msg.call_args_list]
        found = any("mutters something" in c for c in calls)
        self.assertTrue(found, f"Expected mutter message, got: {calls}")


class TestGtellInGroup(EvenniaCommandTest):
    """Test gtell when in a group."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        # char2 follows char1 — forms a group
        self.char1.following = None
        self.char2.following = self.char1

    def test_group_message_to_sender(self):
        """Sender sees their own group message."""
        result = self.call(CmdGtell(), "let's go")
        self.assertIn("[Group]", result)
        self.assertIn("You tell the group", result)
        self.assertIn("let's go", result)

    def test_group_message_to_member(self):
        """Group member receives the message."""
        self.char2.msg = MagicMock()
        self.call(CmdGtell(), "attack now")
        calls = [str(c) for c in self.char2.msg.call_args_list]
        found = any("[Group]" in c and "attack now" in c for c in calls)
        self.assertTrue(found, f"Expected group message, got: {calls}")

    def test_follower_can_gtell(self):
        """A follower (not just leader) can send group messages."""
        result = self.call(CmdGtell(), "I'm here", caller=self.char2)
        self.assertIn("[Group]", result)
        self.assertIn("You tell the group", result)
