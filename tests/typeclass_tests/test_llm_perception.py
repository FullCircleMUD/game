"""
Tests for LLM NPC perception — who appears in the prompt's room context.

An LLM NPC must not be told about a character it cannot perceive, or it
will greet, name and remember someone who is standing there invisible.

LLMRoleplayNPC is used deliberately: it derives from BaseNPC, which has
no ``.ai`` handler, so these also cover the class family that cannot use
AIHandler.get_targets_in_room.

evennia test --settings settings tests.typeclass_tests.test_llm_perception
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaTest

from enums.condition import Condition
from typeclasses.actors.npcs.llm_roleplay_npc import LLMRoleplayNPC


class LLMPerceptionTest(EvenniaTest):
    """An LLM NPC sharing a room with one player character."""

    room_typeclass = "typeclasses.terrain.rooms.room_base.RoomBase"
    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.npc = create_object(
            LLMRoleplayNPC,
            key="Rowan",
            location=self.room1,
        )
        # char1 is the only player in the room
        self.char2.location = self.room2

    def tearDown(self):
        if self.npc and self.npc.pk:
            self.npc.delete()
        super().tearDown()

    def _nearby(self):
        return self.npc._get_context_variables()["nearby_characters"]


class TestNearbyCharacters(LLMPerceptionTest):

    def test_a_visible_player_is_named(self):
        self.assertIn(self.char1.key, self._nearby())

    def test_an_invisible_player_is_not_named(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertNotIn(self.char1.key, self._nearby())

    def test_a_hidden_player_is_not_named(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.assertNotIn(self.char1.key, self._nearby())

    def test_a_room_of_only_concealed_players_reads_as_nobody(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.assertEqual(self._nearby(), "nobody")

    def test_the_npc_does_not_list_itself(self):
        self.assertNotIn(self.npc.key, self._nearby())


class TestCounters(LLMPerceptionTest):

    def test_detect_invis_restores_an_invisible_player(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.npc.add_condition(Condition.DETECT_INVIS)
        self.assertIn(self.char1.key, self._nearby())

    def test_true_sight_restores_a_hidden_player(self):
        self.char1.add_condition(Condition.HIDDEN)
        self.npc.apply_true_sight(duration_seconds=300)
        self.assertIn(self.char1.key, self._nearby())

    def test_true_sight_does_not_restore_an_invisible_player(self):
        self.char1.add_condition(Condition.INVISIBLE)
        self.npc.apply_true_sight(duration_seconds=300)
        self.assertNotIn(self.char1.key, self._nearby())
