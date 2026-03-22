"""
Tests for CmdSay — language-aware say command.

Verifies language switching, garbled output for non-speakers,
COMPREHEND_LANGUAGES bypass, SILENCED/DEAF/INVISIBLE conditions,
and error handling.

evennia test --settings settings tests.command_tests.test_cmd_say
"""

from unittest.mock import PropertyMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_say import CmdSay
from enums.condition import Condition
from utils.garble import garble


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestCmdSay(EvenniaCommandTest):
    """Test the language-aware say command."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        # Both characters know Common by default.
        self.char1.db.languages = {"common"}
        self.char2.db.languages = {"common"}

    def _call_and_capture_listener(self, cmd, input_args, cmdstring=None):
        """Call a command and capture what char2 receives.

        Returns (caller_result, list_of_char2_messages).
        Test chars don't have active sessions so has_account is False;
        we patch it to True for char2 so the per-listener loop includes it.
        """
        received = []
        original_msg = self.char2.msg
        self.char2.msg = lambda text, **kw: received.append(text)

        # Patch has_account on char2's class to return True for char2.
        original_has_account = type(self.char2).has_account
        type(self.char2).has_account = property(lambda self_: True)

        kwargs = {}
        if cmdstring:
            kwargs["cmdstring"] = cmdstring
        caller_result = self.call(cmd, input_args, **kwargs)

        type(self.char2).has_account = original_has_account
        self.char2.msg = original_msg
        return caller_result, received

    # --- Basic say (Common) ---

    def test_say_no_args(self):
        """Empty say should prompt."""
        result = self.call(CmdSay(), "")
        self.assertIn("Say what?", result)

    def test_say_common_caller_message(self):
        """Caller should see 'You say: ...' for Common."""
        result = self.call(CmdSay(), "hello world")
        self.assertIn('You say: "hello world"', result)

    def test_say_common_listener_hears(self):
        """Listener should hear Common speech clearly."""
        _, received = self._call_and_capture_listener(CmdSay(), "hello world")
        combined = " ".join(str(m) for m in received)
        self.assertIn("hello world", combined)

    # --- Language switch ---

    def test_say_dwarven_caller_message(self):
        """Caller should see 'You say in Dwarven: ...'."""
        self.char1.db.languages = {"common", "dwarven"}
        result = self.call(CmdSay(), "hello", cmdstring="say/dwarven")
        self.assertIn('You say in Dwarven: "hello"', result)

    def test_say_dwarven_short_alias(self):
        """Short alias say/dw should work."""
        self.char1.db.languages = {"common", "dwarven"}
        result = self.call(CmdSay(), "hello", cmdstring="say/dw")
        self.assertIn('You say in Dwarven: "hello"', result)

    def test_say_elfish_alias(self):
        """say/el should speak Elfish."""
        self.char1.db.languages = {"common", "elfish"}
        result = self.call(CmdSay(), "hello", cmdstring="say/el")
        self.assertIn('You say in Elfish: "hello"', result)

    def test_say_switch_in_args(self):
        """Live game: switch ends up in args, not cmdname."""
        self.char1.db.languages = {"common", "dwarven"}
        result = self.call(CmdSay(), "/dw hello")
        self.assertIn('You say in Dwarven: "hello"', result)

    # --- Listener understands language ---

    def test_listener_knows_language_hears_clear(self):
        """Listener who knows the language should hear clear text."""
        self.char1.db.languages = {"common", "dwarven"}
        self.char2.db.languages = {"common", "dwarven"}

        _, received = self._call_and_capture_listener(
            CmdSay(), "secret message", cmdstring="say/dw"
        )
        combined = " ".join(str(m) for m in received)
        self.assertIn("secret message", combined)
        self.assertIn("Dwarven", combined)

    # --- Listener does NOT understand language ---

    def test_listener_no_language_hears_garble(self):
        """Listener who doesn't know the language should hear garbled text."""
        self.char1.db.languages = {"common", "dwarven"}
        self.char2.db.languages = {"common"}  # no dwarven

        _, received = self._call_and_capture_listener(
            CmdSay(), "secret message", cmdstring="say/dw"
        )
        combined = " ".join(str(m) for m in received)
        self.assertNotIn("secret message", combined)
        expected_garble = garble("secret message", "dwarven")
        self.assertIn(expected_garble, combined)
        self.assertIn("Dwarven", combined)

    # --- Speaker doesn't know language ---

    def test_speaker_unknown_language(self):
        """Speaker who doesn't know the language should get error."""
        self.char1.db.languages = {"common"}
        result = self.call(CmdSay(), "hello", cmdstring="say/dw")
        self.assertIn("don't know", result.lower())

    # --- Invalid switch ---

    def test_invalid_switch(self):
        """Invalid language switch should show error."""
        result = self.call(CmdSay(), "hello", cmdstring="say/xx")
        self.assertIn("Unknown language switch", result)

    # --- SILENCED condition ---

    def test_silenced_blocks_speech(self):
        """SILENCED caller should not be able to speak."""
        self.char1.add_condition(Condition.SILENCED)
        result = self.call(CmdSay(), "hello")
        self.assertIn("silenced", result.lower())
        self.char1.remove_condition(Condition.SILENCED)

    # --- DEAF listener ---

    def test_deaf_listener_hears_nothing(self):
        """DEAF listener should receive no message."""
        self.char2.add_condition(Condition.DEAF)

        _, received = self._call_and_capture_listener(CmdSay(), "hello")

        self.char2.remove_condition(Condition.DEAF)
        self.assertEqual(len(received), 0)

    # --- COMPREHEND_LANGUAGES ---

    def test_comprehend_languages_bypasses_garble(self):
        """Listener with COMPREHEND_LANGUAGES should understand any language."""
        self.char1.db.languages = {"common", "dragon"}
        self.char2.db.languages = {"common"}  # no dragon
        self.char2.add_condition(Condition.COMPREHEND_LANGUAGES)

        _, received = self._call_and_capture_listener(
            CmdSay(), "ancient words", cmdstring="say/dr"
        )

        self.char2.remove_condition(Condition.COMPREHEND_LANGUAGES)
        combined = " ".join(str(m) for m in received)
        self.assertIn("ancient words", combined)

    # --- INVISIBLE speaker ---

    def test_invisible_speaker_shows_someone(self):
        """Invisible speaker should show 'Someone' to non-DETECT_INVIS."""
        self.char1.add_condition(Condition.INVISIBLE)

        _, received = self._call_and_capture_listener(CmdSay(), "boo")

        self.char1.remove_condition(Condition.INVISIBLE)
        combined = " ".join(str(m) for m in received)
        self.assertIn("Someone", combined)

    def test_invisible_speaker_detect_invis_shows_name(self):
        """DETECT_INVIS listener should see invisible speaker's name."""
        self.char1.add_condition(Condition.INVISIBLE)
        self.char2.add_condition(Condition.DETECT_INVIS)

        _, received = self._call_and_capture_listener(CmdSay(), "boo")

        self.char1.remove_condition(Condition.INVISIBLE)
        self.char2.remove_condition(Condition.DETECT_INVIS)
        combined = " ".join(str(m) for m in received)
        self.assertIn(self.char1.key, combined)
        self.assertNotIn("Someone", combined)
