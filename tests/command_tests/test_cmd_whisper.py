"""
Tests for CmdWhisper — language-aware whisper command.

evennia test --settings settings tests.command_tests.test_cmd_whisper
"""

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_whisper import CmdWhisper
from enums.condition import Condition
from utils.garble import garble


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdWhisper(EvenniaCommandTest):
    """Test the language-aware whisper command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.languages = {"common"}
        self.char2.db.languages = {"common"}

    def _call_and_capture_receiver(self, cmd, input_args, cmdstring=None):
        """Call a command and capture what char2 receives."""
        received = []
        original_msg = self.char2.msg
        self.char2.msg = lambda text, **kw: received.append(text)

        kwargs = {}
        if cmdstring:
            kwargs["cmdstring"] = cmdstring
        caller_result = self.call(cmd, input_args, **kwargs)

        self.char2.msg = original_msg
        return caller_result, received

    # --- Basic whisper ---

    def test_whisper_no_args(self):
        """No arguments gives usage message."""
        self.call(CmdWhisper(), "", "Usage: whisper <character> = <message>")

    def test_whisper_common_caller_message(self):
        """Caller should see 'You whisper to Char2: ...'."""
        result = self.call(CmdWhisper(), "Char2 = hello")
        self.assertIn('You whisper to Char2: "hello"', result)

    def test_whisper_common_receiver_hears(self):
        """Receiver should hear Common whisper clearly."""
        _, received = self._call_and_capture_receiver(
            CmdWhisper(), "Char2 = secret stuff"
        )
        combined = " ".join(str(m) for m in received)
        self.assertIn("secret stuff", combined)

    # --- Language switch ---

    def test_whisper_dwarven_receiver_knows(self):
        """Receiver who knows Dwarven should hear clear text."""
        self.char1.db.languages = {"common", "dwarven"}
        self.char2.db.languages = {"common", "dwarven"}

        _, received = self._call_and_capture_receiver(
            CmdWhisper(), "Char2 = secret words",
            cmdstring="whisper/dw",
        )
        combined = " ".join(str(m) for m in received)
        self.assertIn("secret words", combined)
        self.assertIn("Dwarven", combined)

    def test_whisper_dwarven_receiver_no_language(self):
        """Receiver who doesn't know Dwarven should hear garble."""
        self.char1.db.languages = {"common", "dwarven"}
        self.char2.db.languages = {"common"}

        _, received = self._call_and_capture_receiver(
            CmdWhisper(), "Char2 = secret words",
            cmdstring="whisper/dw",
        )
        combined = " ".join(str(m) for m in received)
        self.assertNotIn("secret words", combined)
        expected_garble = garble("secret words", "dwarven")
        self.assertIn(expected_garble, combined)

    # --- Speaker doesn't know language ---

    def test_speaker_unknown_language(self):
        """Speaker who doesn't know the language should get error."""
        self.char1.db.languages = {"common"}
        result = self.call(
            CmdWhisper(), "Char2 = hello", cmdstring="whisper/dw"
        )
        self.assertIn("don't know", result.lower())

    # --- SILENCED ---

    def test_silenced_blocks_whisper(self):
        """SILENCED caller should not be able to whisper."""
        self.char1.add_condition(Condition.SILENCED)
        result = self.call(CmdWhisper(), "Char2 = hello")
        self.assertIn("silenced", result.lower())
        self.char1.remove_condition(Condition.SILENCED)

    # --- DEAF receiver ---

    def test_deaf_receiver_hears_nothing(self):
        """DEAF receiver should receive no message."""
        self.char2.add_condition(Condition.DEAF)

        _, received = self._call_and_capture_receiver(
            CmdWhisper(), "Char2 = hello"
        )

        self.char2.remove_condition(Condition.DEAF)
        self.assertEqual(len(received), 0)

    # --- COMPREHEND_LANGUAGES ---

    def test_comprehend_languages_bypasses_garble(self):
        """Receiver with COMPREHEND_LANGUAGES should understand any language."""
        self.char1.db.languages = {"common", "dragon"}
        self.char2.db.languages = {"common"}
        self.char2.add_condition(Condition.COMPREHEND_LANGUAGES)

        _, received = self._call_and_capture_receiver(
            CmdWhisper(), "Char2 = ancient secrets",
            cmdstring="whisper/dr",
        )

        self.char2.remove_condition(Condition.COMPREHEND_LANGUAGES)
        combined = " ".join(str(m) for m in received)
        self.assertIn("ancient secrets", combined)

    # --- Invalid switch ---

    def test_invalid_switch(self):
        """Invalid language switch should show error."""
        result = self.call(CmdWhisper(), "Char2 = hello", cmdstring="whisper/xx")
        self.assertIn("Unknown language switch", result)
