"""
Tests for TutorialGuideNPC.

Tests:
    - Guide NPC creation with correct attributes
    - Guide detects guide_context on room entry
    - Guide falls back to tutorial_text when LLM unavailable
    - Guide tracks last_guide_room_id to prevent repeats

evennia test --settings settings tests.tutorial_tests.test_tutorial_guide
"""

from unittest.mock import patch, MagicMock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.terrain.rooms.room_base import RoomBase

_CHAR = "typeclasses.actors.character.FCMCharacter"


class TestTutorialGuideNPC(EvenniaTest):
    """Test TutorialGuideNPC behavior."""

    character_typeclass = _CHAR

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        from typeclasses.actors.npcs.tutorial_guide_npc import TutorialGuideNPC

        self.room1 = create_object(RoomBase, key="Test Room 1")
        self.room1.db.guide_context = "Teach the player to move."
        self.room1.db.tutorial_text = "Tutorial: Movement basics."

        self.room2 = create_object(RoomBase, key="Test Room 2")
        self.room2.db.guide_context = "Teach the player to look."

        self.room_no_context = create_object(RoomBase, key="No Context Room")

        self.guide = create_object(
            TutorialGuideNPC,
            key="Pip",
            location=self.room1,
        )
        self.guide.llm_personality = "A helpful guide."
        self.guide.llm_knowledge = "Base knowledge."

    def test_guide_has_tutorial_item_flag(self):
        """Guide should be flagged as tutorial_item for cleanup."""
        self.assertTrue(self.guide.db.tutorial_item)

    def test_guide_cannot_be_picked_up(self):
        """Guide should have get:false lock."""
        self.assertFalse(self.guide.access(self.char1, "get"))

    def test_guide_detects_guide_context(self):
        """Guide should detect guide_context when entering a room."""
        # Player must be in the target room for guide to speak
        self.char1.move_to(self.room2, quiet=True)
        with patch.object(self.guide, "llm_respond") as mock_respond:
            self.guide.ndb.last_guide_room_id = None
            self.guide.move_to(self.room2)
            mock_respond.assert_called_once()
            call_args = mock_respond.call_args
            # The message should reference the room
            self.assertIn("Test Room 2", call_args[0][1])

    def test_guide_no_speech_without_context(self):
        """Guide should not speak in rooms without guide_context."""
        with patch.object(self.guide, "llm_respond") as mock_respond:
            self.guide.ndb.last_guide_room_id = None
            self.guide.move_to(self.room_no_context)
            mock_respond.assert_not_called()

    def test_guide_no_repeat_speech(self):
        """Guide should not repeat speech when staying in same room."""
        # Player must be in target room for guide to speak
        self.char1.move_to(self.room2, quiet=True)
        with patch.object(self.guide, "llm_respond") as mock_respond:
            self.guide.ndb.last_guide_room_id = None
            self.guide.move_to(self.room2)
            # First entry should speak
            self.assertEqual(mock_respond.call_count, 1)

            # Move to a room without context (no player there, so no speech)
            # then back to room2 — last_guide_room_id is still room2's ID
            mock_respond.reset_mock()
            self.guide.move_to(self.room_no_context)
            self.guide.move_to(self.room2)
            # last_guide_room_id was set to room2.id on first visit,
            # so it should NOT speak again
            mock_respond.assert_not_called()

    def test_fallback_shows_tutorial_text(self):
        """Fallback should show tutorial_text from the room."""
        self.guide.location = self.room1
        result = self.guide.llm_fallback_response(self.char1, "arrive")
        # Should return None (tutorial text sent via msg, no emote)
        self.assertIsNone(result)

    def test_fallback_emote_without_tutorial_text(self):
        """Fallback should show emote if no tutorial_text."""
        self.guide.location = self.room_no_context
        result = self.guide.llm_fallback_response(self.char1, "arrive")
        self.assertIn("Pip", result)

    def test_knowledge_injection_restored(self):
        """Base knowledge should be restored after room speech."""
        original_knowledge = self.guide.llm_knowledge

        with patch.object(self.guide, "llm_respond"):
            self.char1.move_to(self.room2)
            self.guide.ndb.last_guide_room_id = None
            self.guide.move_to(self.room2)

        self.assertEqual(self.guide.llm_knowledge, original_knowledge)
