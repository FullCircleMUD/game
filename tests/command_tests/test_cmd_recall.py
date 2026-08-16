"""
Tests for the recall command — the way back out of a book zone.

evennia test --settings settings tests.command_tests.test_cmd_recall
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_recall import CmdRecall
from utils.busy import BUSY_MESSAGE, check_busy


class TestCmdRecall(EvenniaCommandTest):

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room1.always_lit = True
        self.room2.always_lit = True
        self.char1.db.book_return_location = self.room2

    def _capture(self):
        """Collect what the character is told from here on."""
        said = []
        self.char1.msg = lambda text="", **kwargs: said.append(str(text))
        return said

    def test_nowhere_to_recall_to(self):
        self.char1.db.book_return_location = None
        self.call(CmdRecall(), "", "You have nowhere to recall to.")

    def test_a_recall_holds_the_lock(self):
        self.call(CmdRecall(), "")
        self.assertTrue(self.char1.ndb.is_processing)

    def test_nobody_is_held_when_there_is_nowhere_to_go(self):
        self.char1.db.book_return_location = None
        self.call(CmdRecall(), "")
        self.assertFalse(self.char1.ndb.is_processing)

    def test_a_second_command_is_refused_in_recall_s_wording(self):
        self.call(CmdRecall(), "")
        said = self._capture()
        check_busy(self.char1)
        self.assertIn("You are already recalling.", said)
        self.assertNotIn(BUSY_MESSAGE, said)

    def test_a_recalling_character_cannot_walk_away(self):
        self.call(CmdRecall(), "")
        said = self._capture()
        self.assertFalse(self.char1.at_pre_move(self.room1))
        self.assertIn(
            "The world is fading around you — you can't move.", said
        )

    def test_a_busy_character_cannot_recall(self):
        self.char1.ndb.is_processing = True
        self.call(CmdRecall(), "", BUSY_MESSAGE)
