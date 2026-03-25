"""
Tests for LLM NPC system — LLMMixin, speech detection, and command hooks.

Tests the mixin's speech detection modes, memory management, response
sanitization, and integration with say/whisper commands. LLM API calls
are mocked — no real API calls are made.

evennia test --settings settings tests.command_tests.test_llm_npc
"""

from unittest.mock import MagicMock, patch

from evennia.utils.test_resources import EvenniaCommandTest

from commands.all_char_cmds.cmd_say import CmdSay


def _immediate_call_later(delay, fn, *args, **kwargs):
    """Execute reactor.callLater callbacks immediately for testing."""
    return fn(*args, **kwargs)


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"


class TestLLMMixin(EvenniaCommandTest):
    """Test LLMMixin speech detection and memory."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.languages = {"common"}
        self.char2.db.languages = {"common"}

    def _create_llm_npc(self, **kwargs):
        """Create an LLMRoleplayNPC in the test room."""
        from evennia.utils.create import create_object

        npc = create_object(
            "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
            key=kwargs.get("key", "Brom the Blacksmith"),
            location=self.room1,
        )
        npc.llm_personality = kwargs.get(
            "personality", "A gruff blacksmith."
        )
        npc.llm_knowledge = kwargs.get("knowledge", "Sells swords.")
        for k, v in kwargs.items():
            if k.startswith("llm_"):
                setattr(npc, k, v)
        return npc

    # --- Name match detection ---

    def test_name_match_full_name(self):
        """Name match should detect full NPC name in speech."""
        from typeclasses.mixins.llm_mixin import LLMMixin

        npc = self._create_llm_npc()
        self.assertTrue(npc._name_mentioned_in("hey Brom the Blacksmith, got swords?"))

    def test_name_match_partial_name(self):
        """Name match should detect partial name (single word >= 3 chars)."""
        npc = self._create_llm_npc()
        self.assertTrue(npc._name_mentioned_in("hey Brom do you have swords?"))

    def test_name_match_case_insensitive(self):
        """Name match should be case-insensitive."""
        npc = self._create_llm_npc()
        self.assertTrue(npc._name_mentioned_in("BROM sell me a sword"))

    def test_name_match_no_match(self):
        """Name match should not trigger for unrelated speech."""
        npc = self._create_llm_npc()
        self.assertFalse(npc._name_mentioned_in("I want to buy a sword"))

    def test_name_match_short_words_ignored(self):
        """Words shorter than 3 chars from the NPC name should be ignored."""
        npc = self._create_llm_npc(key="Ax the Bold")
        # "Ax" is only 2 chars, shouldn't match on its own
        self.assertFalse(npc._name_mentioned_in("I need an ax"))
        # But "Bold" should match
        self.assertTrue(npc._name_mentioned_in("hey Bold one"))

    # --- Speech mode: whisper_only ---

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_whisper_only_ignores_say(self, mock_respond):
        """whisper_only mode should ignore say speech."""
        npc = self._create_llm_npc(llm_speech_mode="whisper_only")
        npc.at_llm_say_heard(self.char1, "hey Brom", language="common")
        mock_respond.assert_not_called()

    # --- Speech mode: always ---

    @patch("twisted.internet.reactor.callLater", side_effect=_immediate_call_later)
    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_always_responds_to_any_speech(self, mock_respond, _mock_cl):
        """always mode should respond to any speech."""
        npc = self._create_llm_npc(llm_speech_mode="always")
        npc.at_llm_say_heard(self.char1, "random chatter", language="common")
        mock_respond.assert_called_once()

    # --- Speech mode: name_match ---

    @patch("twisted.internet.reactor.callLater", side_effect=_immediate_call_later)
    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_name_match_triggers_response(self, mock_respond, _mock_cl):
        """name_match mode should trigger when NPC name is in speech."""
        npc = self._create_llm_npc(llm_speech_mode="name_match")
        npc.at_llm_say_heard(self.char1, "hey Brom got swords?", language="common")
        mock_respond.assert_called_once()

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_name_match_no_trigger_without_name(self, mock_respond):
        """name_match mode should not trigger without NPC name."""
        npc = self._create_llm_npc(llm_speech_mode="name_match")
        npc.at_llm_say_heard(self.char1, "anyone got swords?", language="common")
        mock_respond.assert_not_called()

    # --- Conversation engagement ---

    @patch("twisted.internet.reactor.callLater", side_effect=_immediate_call_later)
    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_engaged_speaker_gets_response_without_name(self, mock_respond, _mock_cl):
        """After NPC responds, follow-up speech should trigger without name."""
        import time as _time

        npc = self._create_llm_npc(llm_speech_mode="name_match")
        # Simulate NPC having just responded to char1
        npc.ndb.llm_engaged_with = {
            "speaker_id": self.char1.id,
            "time": _time.time(),
        }
        npc.at_llm_say_heard(self.char1, "what about shields?", language="common")
        mock_respond.assert_called_once()

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_engagement_expires(self, mock_respond):
        """Engagement should expire after timeout."""
        import time as _time

        npc = self._create_llm_npc(llm_speech_mode="name_match")
        npc.llm_engagement_timeout = 10
        # Simulate engagement that expired 20 seconds ago
        npc.ndb.llm_engaged_with = {
            "speaker_id": self.char1.id,
            "time": _time.time() - 20,
        }
        npc.at_llm_say_heard(self.char1, "what about shields?", language="common")
        mock_respond.assert_not_called()

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_engagement_only_for_same_speaker(self, mock_respond):
        """Engagement should not carry over to a different speaker."""
        import time as _time

        npc = self._create_llm_npc(llm_speech_mode="name_match")
        npc.ndb.llm_engaged_with = {
            "speaker_id": self.char1.id,
            "time": _time.time(),
        }
        # char2 speaks without saying the name — should NOT trigger
        npc.at_llm_say_heard(self.char2, "what about shields?", language="common")
        mock_respond.assert_not_called()

    # --- Hook enables ---

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_disabled_say_hook_ignores_speech(self, mock_respond):
        """Disabled say hook should ignore all speech."""
        npc = self._create_llm_npc(
            llm_speech_mode="always", llm_hook_say=False
        )
        npc.at_llm_say_heard(self.char1, "hey Brom", language="common")
        mock_respond.assert_not_called()

    @patch("twisted.internet.reactor.callLater", side_effect=_immediate_call_later)
    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_whisper_hook_triggers(self, mock_respond, _mock_cl):
        """Whisper hook should trigger when enabled."""
        npc = self._create_llm_npc()
        npc.at_llm_whisper_received(self.char1, "secret message")
        mock_respond.assert_called_once_with(
            self.char1, "secret message", interaction_type="whisper"
        )

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_disabled_whisper_hook_ignores(self, mock_respond):
        """Disabled whisper hook should ignore whispers."""
        npc = self._create_llm_npc(llm_hook_whisper=False)
        npc.at_llm_whisper_received(self.char1, "secret message")
        mock_respond.assert_not_called()

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_arrive_hook_triggers(self, mock_respond):
        """Arrive hook should trigger when enabled."""
        npc = self._create_llm_npc(llm_hook_arrive=True)
        npc.at_llm_player_arrive(self.char1)
        mock_respond.assert_called_once()

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_arrive_hook_disabled_by_default(self, mock_respond):
        """Arrive hook should be disabled by default."""
        npc = self._create_llm_npc()
        npc.at_llm_player_arrive(self.char1)
        mock_respond.assert_not_called()

    # --- Non-common language ignored ---

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_non_common_language_ignored(self, mock_respond):
        """NPCs should ignore non-Common speech (for now)."""
        npc = self._create_llm_npc(llm_speech_mode="always")
        npc.at_llm_say_heard(self.char1, "hello", language="dwarven")
        mock_respond.assert_not_called()

    # --- LLM disabled ---

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.llm_respond")
    def test_disabled_npc_ignores_everything(self, mock_respond):
        """Disabled NPC should ignore all triggers."""
        npc = self._create_llm_npc(llm_enabled=False, llm_speech_mode="always")
        npc.at_llm_say_heard(self.char1, "hello", language="common")
        npc.at_llm_whisper_received(self.char1, "hello")
        mock_respond.assert_not_called()

    # --- Memory ---

    def test_store_and_retrieve_memory(self):
        """Memory should store and retrieve conversation history."""
        npc = self._create_llm_npc()
        npc._store_memory("TestPlayer", "hello", "greetings!")
        history = npc.db.llm_conversation_history
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[0]["speaker"], "TestPlayer")
        self.assertEqual(history[1]["role"], "assistant")

    def test_memory_trimming(self):
        """Memory should trim to max entries."""
        npc = self._create_llm_npc()
        npc.llm_memory_max_entries = 4  # 2 exchanges
        npc._store_memory("P1", "msg1", "resp1")
        npc._store_memory("P2", "msg2", "resp2")
        npc._store_memory("P3", "msg3", "resp3")
        history = npc.db.llm_conversation_history
        self.assertEqual(len(history), 4)
        # Oldest (P1) should be trimmed
        self.assertEqual(history[0]["speaker"], "P2")

    def test_clear_memory(self):
        """clear_llm_memory should wipe history."""
        npc = self._create_llm_npc()
        npc._store_memory("P1", "msg1", "resp1")
        self.assertTrue(len(npc.db.llm_conversation_history) > 0)
        npc.clear_llm_memory()
        self.assertEqual(len(npc.db.llm_conversation_history), 0)

    # --- Response sanitization ---

    def test_sanitize_strips_quotes(self):
        """Sanitize should strip surrounding quotes."""
        from typeclasses.mixins.llm_mixin import LLMMixin

        self.assertEqual(LLMMixin._sanitize_response('"hello there"'), "hello there")

    def test_sanitize_removes_command_prefix(self):
        """Sanitize should remove command-like prefixes."""
        from typeclasses.mixins.llm_mixin import LLMMixin

        self.assertEqual(LLMMixin._sanitize_response("say hello"), "hello")
        self.assertEqual(LLMMixin._sanitize_response("whisper secret"), "secret")

    def test_sanitize_collapses_newlines(self):
        """Sanitize should collapse newlines to spaces."""
        from typeclasses.mixins.llm_mixin import LLMMixin

        self.assertEqual(
            LLMMixin._sanitize_response("line one\nline two"), "line one line two"
        )

    def test_sanitize_truncates(self):
        """Sanitize should truncate to 500 chars."""
        from typeclasses.mixins.llm_mixin import LLMMixin

        long_text = "a" * 600
        result = LLMMixin._sanitize_response(long_text)
        self.assertEqual(len(result), 500)
        self.assertTrue(result.endswith("..."))


class TestSayLLMIntegration(EvenniaCommandTest):
    """Test that CmdSay notifies LLM NPCs."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.languages = {"common"}

    @patch("typeclasses.mixins.llm_mixin.LLMMixin.at_llm_say_heard")
    def test_say_notifies_llm_npc(self, mock_heard):
        """CmdSay should call at_llm_say_heard on LLM NPCs in the room."""
        from evennia.utils.create import create_object

        npc = create_object(
            "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
            key="TestNPC",
            location=self.room1,
        )

        self.call(CmdSay(), "hello world")

        mock_heard.assert_called_once_with(
            speaker=self.char1, message="hello world", language="common"
        )
