"""
Tests for the ai_memory system — NPC vector memory with embeddings.

Tests the memory services (store, search, recent, time_ago), the
LLMMixin vector memory routing, and the NpcMemory model. Embedding
API calls are mocked — no real API calls are made.

evennia test --settings settings tests.command_tests.test_ai_memory
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import numpy as np
from django.utils import timezone
from evennia.utils.test_resources import EvenniaCommandTest

from ai_memory.services import _cosine_similarity, _time_ago_str


WALLET_A = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"

# A fixed 1536-dim embedding for mocking
MOCK_EMBEDDING = list(np.random.RandomState(42).randn(1536).astype(np.float32))
# A different embedding for contrast
MOCK_EMBEDDING_2 = list(np.random.RandomState(99).randn(1536).astype(np.float32))


class TestCosineSimlarity(EvenniaCommandTest):
    """Test numpy cosine similarity utility."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_identical_vectors(self):
        """Identical vectors should have similarity ~1.0."""
        vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        self.assertAlmostEqual(_cosine_similarity(vec, vec), 1.0, places=5)

    def test_orthogonal_vectors(self):
        """Orthogonal vectors should have similarity ~0.0."""
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        self.assertAlmostEqual(_cosine_similarity(a, b), 0.0, places=5)

    def test_opposite_vectors(self):
        """Opposite vectors should have similarity ~-1.0."""
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([-1.0, 0.0], dtype=np.float32)
        self.assertAlmostEqual(_cosine_similarity(a, b), -1.0, places=5)


class TestTimeAgoStr(EvenniaCommandTest):
    """Test human-readable time formatting."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_minutes_ago(self):
        dt = timezone.now() - timedelta(minutes=5)
        self.assertEqual(_time_ago_str(dt), "a few minutes ago")

    def test_earlier_today(self):
        dt = timezone.now() - timedelta(hours=5)
        self.assertEqual(_time_ago_str(dt), "earlier today")

    def test_yesterday(self):
        dt = timezone.now() - timedelta(hours=30)
        self.assertEqual(_time_ago_str(dt), "yesterday")

    def test_few_days_ago(self):
        dt = timezone.now() - timedelta(days=4)
        self.assertEqual(_time_ago_str(dt), "a few days ago")

    def test_weeks_ago(self):
        dt = timezone.now() - timedelta(days=20)
        self.assertEqual(_time_ago_str(dt), "a couple of weeks ago")

    def test_months_ago_includes_month_name(self):
        dt = timezone.now() - timedelta(days=90)
        result = _time_ago_str(dt)
        self.assertTrue(result.startswith("back in "))

    def test_over_a_year_ago(self):
        dt = timezone.now() - timedelta(days=400)
        self.assertEqual(_time_ago_str(dt), "over a year ago")


class TestNpcMemoryModel(EvenniaCommandTest):
    """Test NpcMemory model CRUD operations."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_create_memory(self):
        """Should be able to create a memory record."""
        from ai_memory.models import NpcMemory

        mem = NpcMemory.objects.using("ai_memory").create(
            npc_id=1,
            speaker_id=2,
            speaker_name="TestPlayer",
            npc_name="TestNPC",
            user_message="hello",
            assistant_message="greetings!",
            summary="TestPlayer said hello, TestNPC replied greetings",
            interaction_type="say",
        )
        self.assertEqual(mem.npc_name, "TestNPC")
        self.assertEqual(mem.speaker_name, "TestPlayer")

    def test_embedding_storage(self):
        """Should store and retrieve numpy arrays as binary blobs."""
        from ai_memory.models import NpcMemory

        vec = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        mem = NpcMemory.objects.using("ai_memory").create(
            npc_id=1,
            speaker_id=2,
            speaker_name="Player",
            npc_name="NPC",
            user_message="test",
            assistant_message="test reply",
            embedding=vec.tobytes(),
        )
        loaded = NpcMemory.objects.using("ai_memory").get(pk=mem.pk)
        loaded_vec = np.frombuffer(bytes(loaded.embedding), dtype=np.float32)
        np.testing.assert_array_equal(loaded_vec, vec)

    def test_name_based_query(self):
        """Should be able to query by NPC name (for DB wipe recovery)."""
        from ai_memory.models import NpcMemory

        NpcMemory.objects.using("ai_memory").create(
            npc_id=999,
            speaker_id=888,
            speaker_name="OldPlayer",
            npc_name="Chatty",
            user_message="hi chatty",
            assistant_message="howdy!",
        )
        results = NpcMemory.objects.using("ai_memory").filter(npc_name="Chatty")
        self.assertEqual(results.count(), 1)


class TestMemoryServices(EvenniaCommandTest):
    """Test ai_memory service functions."""

    databases = "__all__"

    def create_script(self):
        pass

    @patch("llm.service.LLMService.create_embedding", return_value=MOCK_EMBEDDING)
    def test_store_memory(self, mock_embed):
        """store_memory should create a record with embedding."""
        from ai_memory.models import NpcMemory
        from ai_memory.services import store_memory

        npc = MagicMock(id=10, key="TestNPC")
        speaker = MagicMock(id=20, key="Player1")

        store_memory(npc, speaker, "hello", "hi there!")

        mems = NpcMemory.objects.using("ai_memory").filter(npc_id=10)
        self.assertEqual(mems.count(), 1)
        mem = mems.first()
        self.assertEqual(mem.speaker_name, "Player1")
        self.assertIsNotNone(mem.embedding)
        mock_embed.assert_called_once()

    @patch("llm.service.LLMService.create_embedding", return_value=None)
    def test_store_memory_without_embedding(self, mock_embed):
        """store_memory should still save even if embedding fails."""
        from ai_memory.models import NpcMemory
        from ai_memory.services import store_memory

        npc = MagicMock(id=11, key="TestNPC")
        speaker = MagicMock(id=21, key="Player1")

        store_memory(npc, speaker, "hello", "hi there!")

        mems = NpcMemory.objects.using("ai_memory").filter(npc_id=11)
        self.assertEqual(mems.count(), 1)
        self.assertIsNone(mems.first().embedding)

    @patch("llm.service.LLMService.create_embedding")
    def test_search_memories_semantic(self, mock_embed):
        """search_memories should rank by cosine similarity."""
        from ai_memory.models import NpcMemory
        from ai_memory.services import search_memories

        # Store two memories with different embeddings
        vec1 = np.random.RandomState(1).randn(1536).astype(np.float32)
        vec2 = np.random.RandomState(2).randn(1536).astype(np.float32)

        NpcMemory.objects.using("ai_memory").create(
            npc_id=30, speaker_id=40, speaker_name="P",
            npc_name="N", user_message="about swords",
            assistant_message="I sell swords", embedding=vec1.tobytes(),
        )
        NpcMemory.objects.using("ai_memory").create(
            npc_id=30, speaker_id=40, speaker_name="P",
            npc_name="N", user_message="about magic",
            assistant_message="I know nothing of magic", embedding=vec2.tobytes(),
        )

        # Query embedding is identical to vec1 — should rank first
        mock_embed.return_value = list(vec1)
        results = search_memories(npc_id=30, query_text="swords")

        self.assertEqual(len(results), 2)
        self.assertGreater(results[0]["similarity"], results[1]["similarity"])
        self.assertIn("swords", results[0]["user_message"])

    def test_get_recent_memories(self):
        """get_recent_memories should return chronological order."""
        from ai_memory.models import NpcMemory
        from ai_memory.services import get_recent_memories

        NpcMemory.objects.using("ai_memory").create(
            npc_id=50, speaker_id=60, speaker_name="P",
            npc_name="N", user_message="first", assistant_message="reply1",
        )
        NpcMemory.objects.using("ai_memory").create(
            npc_id=50, speaker_id=60, speaker_name="P",
            npc_name="N", user_message="second", assistant_message="reply2",
        )

        results = get_recent_memories(npc_id=50, limit=10)
        self.assertEqual(len(results), 2)
        # Should be chronological (oldest first)
        self.assertEqual(results[0]["user_message"], "first")
        self.assertEqual(results[1]["user_message"], "second")

    def test_name_fallback_search(self):
        """search_memories should fall back to name if ID returns nothing."""
        from ai_memory.models import NpcMemory
        from ai_memory.services import get_recent_memories

        # Memory stored with old npc_id
        NpcMemory.objects.using("ai_memory").create(
            npc_id=999, speaker_id=888, speaker_name="Player",
            npc_name="Chatty", user_message="hello",
            assistant_message="howdy!",
        )

        # Query with new npc_id but same name
        results = get_recent_memories(npc_id=777, npc_name="Chatty")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["user_message"], "hello")

    def test_get_last_interaction_time(self):
        """get_last_interaction_time should return the most recent datetime."""
        from ai_memory.models import NpcMemory
        from ai_memory.services import get_last_interaction_time

        NpcMemory.objects.using("ai_memory").create(
            npc_id=70, speaker_id=80, speaker_name="Tim",
            npc_name="Chatty", user_message="hey",
            assistant_message="hello!",
        )

        dt, time_ago = get_last_interaction_time(npc_id=70, speaker_id=80)
        self.assertIsNotNone(dt)
        self.assertEqual(time_ago, "a few minutes ago")

    def test_get_last_interaction_time_no_history(self):
        """get_last_interaction_time should return None for no history."""
        from ai_memory.services import get_last_interaction_time

        dt, time_ago = get_last_interaction_time(npc_id=9999, speaker_id=9998)
        self.assertIsNone(dt)
        self.assertIsNone(time_ago)


class TestLLMMixinVectorRouting(EvenniaCommandTest):
    """Test that LLMMixin routes to vector or rolling list by flag."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.account.attributes.add("wallet_address", WALLET_A)
        self.char1.db.languages = {"common"}

    def _create_llm_npc(self, **kwargs):
        from evennia.utils.create import create_object

        npc = create_object(
            "typeclasses.actors.npcs.llm_roleplay_npc.LLMRoleplayNPC",
            key=kwargs.get("key", "TestNPC"),
            location=self.room1,
        )
        npc.llm_personality = kwargs.get("personality", "A test NPC.")
        for k, v in kwargs.items():
            if k.startswith("llm_"):
                setattr(npc, k, v)
        return npc

    def test_default_uses_rolling_list(self):
        """Default NPC should use rolling list memory."""
        npc = self._create_llm_npc()
        self.assertFalse(npc.llm_use_vector_memory)
        npc._store_memory("Player", "hello", "hi!")
        # Should be in rolling list
        history = npc.db.llm_conversation_history
        self.assertEqual(len(history), 2)

    @patch("ai_memory.services.store_memory")
    def test_vector_flag_routes_to_ai_memory(self, mock_store):
        """NPC with llm_use_vector_memory=True should route to ai_memory."""
        npc = self._create_llm_npc(llm_use_vector_memory=True)
        npc.ndb._llm_current_speaker = self.char1
        npc._store_memory("Player", "hello", "hi!")
        mock_store.assert_called_once()
        # Should NOT be in rolling list
        history = npc.db.llm_conversation_history or []
        self.assertEqual(len(history), 0)

    @patch("ai_memory.services.store_memory", side_effect=Exception("db error"))
    def test_vector_store_falls_back_on_error(self, mock_store):
        """Vector store failure should fall back to rolling list."""
        npc = self._create_llm_npc(llm_use_vector_memory=True)
        npc.ndb._llm_current_speaker = self.char1
        npc._store_memory("Player", "hello", "hi!")
        # Should have fallen back to rolling list
        history = npc.db.llm_conversation_history
        self.assertEqual(len(history), 2)

    @patch("ai_memory.services.search_memories")
    def test_vector_get_memories_returns_formatted(self, mock_search):
        """Vector get_relevant_memories should format results as chat messages."""
        mock_search.return_value = [
            {
                "summary": "test",
                "user_message": "hello",
                "assistant_message": "greetings!",
                "similarity": 0.9,
                "created_at": timezone.now(),
                "time_ago": "yesterday",
                "speaker_name": "Tim",
            }
        ]
        npc = self._create_llm_npc(llm_use_vector_memory=True)
        messages = npc._get_relevant_memories(self.char1, "hello")
        self.assertEqual(len(messages), 2)  # user + assistant
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

    @patch("ai_memory.services.get_recent_memories")
    def test_vector_format_memories_includes_timestamps(self, mock_recent):
        """Vector format_memories should include time_ago in output."""
        mock_recent.return_value = [
            {
                "user_message": "hi chatty",
                "assistant_message": "howdy!",
                "time_ago": "yesterday",
                "speaker_name": "Tim",
            }
        ]
        npc = self._create_llm_npc(llm_use_vector_memory=True)
        result = npc._format_memories()
        self.assertIn("(yesterday)", result)
        self.assertIn("Tim", result)
