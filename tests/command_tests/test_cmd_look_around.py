"""
Tests for 'look around' alias — should behave identically to bare 'look'.
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_override_look import CmdLook


class TestCmdLookAround(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True

    def test_look_around_shows_room(self):
        """'look around' should show the room name, same as bare 'look'."""
        result = self.call(CmdLook(), "around")
        self.assertIn(self.room1.key, result)

    def test_look_around_matches_bare_look(self):
        """'look around' and 'look' should produce the same output."""
        bare = self.call(CmdLook(), "")
        around = self.call(CmdLook(), "around")
        self.assertEqual(bare, around)
