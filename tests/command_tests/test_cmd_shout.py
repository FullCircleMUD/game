"""
Tests for CmdShout — language-aware shout with adjacent room support.

evennia test --settings settings tests.command_tests.test_cmd_shout
"""

from evennia.utils import create
from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_shout import CmdShout, _muffle
from enums.condition import Condition
from utils.garble import garble


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdShout(EvenniaCommandTest):
    """Test the language-aware shout command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.languages = {"common"}
        self.char2.db.languages = {"common"}

    def _call_and_capture_listener(self, cmd, input_args, cmdstring=None):
        """Call a command and capture what char2 receives."""
        received = []
        original_msg = self.char2.msg
        self.char2.msg = lambda text, **kw: received.append(text)

        original_has_account = type(self.char2).has_account
        type(self.char2).has_account = property(lambda self_: True)

        kwargs = {}
        if cmdstring:
            kwargs["cmdstring"] = cmdstring
        caller_result = self.call(cmd, input_args, **kwargs)

        type(self.char2).has_account = original_has_account
        self.char2.msg = original_msg
        return caller_result, received

    # --- Basic shout ---

    def test_shout_no_args(self):
        """No arguments gives error."""
        self.call(CmdShout(), "", "Shout what?")

    def test_shout_common_caller_message(self):
        """Caller should see 'You shout: ...'."""
        result = self.call(CmdShout(), "hello world")
        self.assertIn('You shout: "hello world"', result)

    def test_shout_common_listener_hears(self):
        """Same-room listener should hear full shout."""
        _, received = self._call_and_capture_listener(CmdShout(), "hello world")
        combined = " ".join(str(m) for m in received)
        self.assertIn("hello world", combined)
        self.assertIn("shouts", combined)

    # --- Language switch ---

    def test_shout_dwarven_garble(self):
        """Listener who doesn't know Dwarven hears garbled shout."""
        self.char1.db.languages = {"common", "dwarven"}
        self.char2.db.languages = {"common"}

        _, received = self._call_and_capture_listener(
            CmdShout(), "secret message", cmdstring="shout/dw"
        )
        combined = " ".join(str(m) for m in received)
        self.assertNotIn("secret message", combined)
        expected_garble = garble("secret message", "dwarven")
        self.assertIn(expected_garble, combined)
        self.assertIn("Dwarven", combined)

    # --- SILENCED ---

    def test_silenced_blocks_shout(self):
        """SILENCED caller should not be able to shout."""
        self.char1.add_condition(Condition.SILENCED)
        result = self.call(CmdShout(), "hello")
        self.assertIn("silenced", result.lower())
        self.char1.remove_condition(Condition.SILENCED)

    # --- DEAF listener ---

    def test_deaf_listener_hears_nothing(self):
        """DEAF listener should receive no shout message."""
        self.char2.add_condition(Condition.DEAF)

        _, received = self._call_and_capture_listener(CmdShout(), "hello")

        self.char2.remove_condition(Condition.DEAF)
        self.assertEqual(len(received), 0)

    # --- COMPREHEND_LANGUAGES ---

    def test_comprehend_languages_bypasses_garble(self):
        """Listener with COMPREHEND_LANGUAGES should understand any language."""
        self.char1.db.languages = {"common", "dragon"}
        self.char2.db.languages = {"common"}
        self.char2.add_condition(Condition.COMPREHEND_LANGUAGES)

        _, received = self._call_and_capture_listener(
            CmdShout(), "ancient words", cmdstring="shout/dr"
        )

        self.char2.remove_condition(Condition.COMPREHEND_LANGUAGES)
        combined = " ".join(str(m) for m in received)
        self.assertIn("ancient words", combined)

    # --- Invalid switch ---

    def test_invalid_switch(self):
        """Invalid language switch should show error."""
        result = self.call(CmdShout(), "hello", cmdstring="shout/xx")
        self.assertIn("Unknown language switch", result)

    # --- Muffle helper ---

    def test_muffle_short_text(self):
        """Short text (<=3 words) should not be muffled."""
        self.assertEqual(_muffle("hello world"), "hello world")

    def test_muffle_long_text(self):
        """Long text should be truncated to 3 words + '...'."""
        self.assertEqual(
            _muffle("secret meeting tonight at the tavern"),
            "secret meeting tonight...",
        )

    # --- Adjacent room ---

    def test_adjacent_room_hears_muffled_shout(self):
        """Character in adjacent room hears muffled shout with direction."""
        from utils.exit_helpers import connect_bidirectional_exit

        # Create adjacent room and connect via "north" exit
        adj_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Adjacent Room",
            nohome=True,
        )
        connect_bidirectional_exit(self.room1, adj_room, "north")

        # Move char2 to adjacent room
        self.char2.location = adj_room
        self.char2.move_to(adj_room, quiet=True)

        # Capture messages to char2 in adjacent room
        received = []
        original_msg = self.char2.msg
        self.char2.msg = lambda text, **kw: received.append(text)
        original_has_account = type(self.char2).has_account
        type(self.char2).has_account = property(lambda self_: True)

        self.call(CmdShout(), "secret meeting tonight at the tavern")

        type(self.char2).has_account = original_has_account
        self.char2.msg = original_msg

        combined = " ".join(str(m) for m in received)
        # Should hear muffled version from the south (opposite of north)
        self.assertIn("muffled shout", combined)
        self.assertIn("from the south", combined)
        self.assertIn("secret meeting tonight...", combined)

    def test_adjacent_room_language_garble(self):
        """Adjacent room hears garbled muffled text in foreign language."""
        from utils.exit_helpers import connect_bidirectional_exit

        adj_room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Adjacent Room 2",
            nohome=True,
        )
        connect_bidirectional_exit(self.room1, adj_room, "east")

        self.char1.db.languages = {"common", "dwarven"}
        self.char2.db.languages = {"common"}
        self.char2.move_to(adj_room, quiet=True)

        received = []
        original_msg = self.char2.msg
        self.char2.msg = lambda text, **kw: received.append(text)
        original_has_account = type(self.char2).has_account
        type(self.char2).has_account = property(lambda self_: True)

        self.call(
            CmdShout(), "secret meeting tonight at the tavern",
            cmdstring="shout/dw",
        )

        type(self.char2).has_account = original_has_account
        self.char2.msg = original_msg

        combined = " ".join(str(m) for m in received)
        self.assertIn("muffled shout", combined)
        self.assertIn("Dwarven", combined)
        self.assertIn("from the west", combined)
        # Should NOT contain the original text
        self.assertNotIn("secret meeting tonight", combined)
        # Should contain the garbled muffled text
        muffled = _muffle("secret meeting tonight at the tavern")
        expected_garble = garble(muffled, "dwarven")
        self.assertIn(expected_garble, combined)
