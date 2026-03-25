"""
Tests for the Oakwright Timber quest.

Covers: quest registration, acceptance, delivery turn-in, completion,
reward, non-repeatable, and edge cases.

evennia test --settings settings tests.quest_tests.test_oakwright_timber
"""

from unittest.mock import patch

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.actors.npcs.oakwright_npc import (
    OakwrightNPC,
    GENERIC_CONTEXT,
    QUEST_ACTIVE_CONTEXT,
    QUEST_DONE_CONTEXT,
    QUEST_PITCH_CONTEXT,
)
from typeclasses.mixins.quest_giver import CmdNPCQuest
from world.quests.oakwright_timber import OakwrightTimberQuest, TIMBER_ID, TIMBER_NEEDED


class TestOakwrightTimberRegistration(EvenniaCommandTest):
    """Test quest is registered and discoverable."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_registered_in_registry(self):
        from world.quests import get_quest
        self.assertIs(get_quest("oakwright_timber"), OakwrightTimberQuest)

    def test_quest_metadata(self):
        self.assertEqual(OakwrightTimberQuest.key, "oakwright_timber")
        self.assertEqual(OakwrightTimberQuest.name, "Timber for the Workshop")
        self.assertEqual(OakwrightTimberQuest.quest_type, "side")
        self.assertFalse(OakwrightTimberQuest.repeatable)
        self.assertEqual(OakwrightTimberQuest.reward_xp, 100)
        self.assertEqual(OakwrightTimberQuest.reward_gold, 5)


class TestOakwrightTimberAccept(EvenniaCommandTest):
    """Test quest acceptance via CmdNPCQuest."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.oakwright = create_object(
            OakwrightNPC, key="Master Oakwright", location=self.room1
        )
        self.oakwright.quest_key = "oakwright_timber"
        self.oakwright.trainable_skills = ["carpentry"]
        self.oakwright.trainer_masteries = {"carpentry": 2}

    def tearDown(self):
        if self.oakwright and self.oakwright.pk:
            self.oakwright.delete()
        super().tearDown()

    def test_accept_quest(self):
        """quest accept adds the quest to the character."""
        result = self.call(CmdNPCQuest(), "accept", obj=self.oakwright)
        self.assertIn("accepted", result.lower())
        self.assertTrue(self.char1.quests.has("oakwright_timber"))

    def test_accept_shows_help(self):
        """quest accept shows the help text for the first step."""
        result = self.call(CmdNPCQuest(), "accept", obj=self.oakwright)
        self.assertIn("Timber", result)

    def test_accept_already_active(self):
        """quest accept when already on quest says so."""
        self.char1.quests.add(OakwrightTimberQuest)
        result = self.call(CmdNPCQuest(), "accept", obj=self.oakwright)
        self.assertIn("already on", result.lower())

    def test_accept_already_completed(self):
        """quest accept when completed says so (non-repeatable)."""
        quest = self.char1.quests.add(OakwrightTimberQuest)
        quest.status = "completed"
        result = self.call(CmdNPCQuest(), "accept", obj=self.oakwright)
        self.assertIn("already completed", result.lower())


class TestOakwrightTimberDelivery(EvenniaCommandTest):
    """Test timber delivery and turn-in mechanics."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.oakwright = create_object(
            OakwrightNPC, key="Master Oakwright", location=self.room1
        )
        self.oakwright.quest_key = "oakwright_timber"
        self.oakwright.trainable_skills = ["carpentry"]
        self.oakwright.trainer_masteries = {"carpentry": 2}

    def tearDown(self):
        if self.oakwright and self.oakwright.pk:
            self.oakwright.delete()
        super().tearDown()

    def test_turn_in_no_timber(self):
        """Viewing quest with no timber shows shortage message."""
        self.char1.quests.add(OakwrightTimberQuest)
        result = self.call(CmdNPCQuest(), "", obj=self.oakwright)
        self.assertIn("In Progress", result)

    def test_turn_in_partial_timber(self):
        """Viewing quest with partial timber still in progress."""
        self.char1.quests.add(OakwrightTimberQuest)
        resources = self.char1.db.resources or {}
        resources[TIMBER_ID] = 2
        self.char1.db.resources = resources

        result = self.call(CmdNPCQuest(), "", obj=self.oakwright)
        self.assertIn("In Progress", result)

    def test_turn_in_enough_timber(self):
        """Viewing quest with 4+ timber completes the quest."""
        quest = self.char1.quests.add(OakwrightTimberQuest)

        resources = self.char1.db.resources or {}
        resources[TIMBER_ID] = TIMBER_NEEDED
        self.char1.db.resources = resources

        with patch.object(self.char1, "return_resource_to_sink"), \
             patch.object(self.char1, "receive_gold_from_reserve"), \
             patch.object(self.char1, "receive_resource_from_reserve"):
            result = self.call(CmdNPCQuest(), "", obj=self.oakwright)

        quest = self.char1.quests.get("oakwright_timber")
        self.assertTrue(quest.is_completed)

    def test_timber_consumed_on_turn_in(self):
        """return_resource_to_sink is called with correct args."""
        self.char1.quests.add(OakwrightTimberQuest)

        resources = self.char1.db.resources or {}
        resources[TIMBER_ID] = 6  # More than needed
        self.char1.db.resources = resources

        with patch.object(self.char1, "return_resource_to_sink") as mock_sink, \
             patch.object(self.char1, "receive_gold_from_reserve"), \
             patch.object(self.char1, "receive_resource_from_reserve"):
            self.call(CmdNPCQuest(), "", obj=self.oakwright)

        mock_sink.assert_called_once_with(TIMBER_ID, TIMBER_NEEDED)

    def test_completion_message(self):
        """Oakwright's custom completion message is shown."""
        quest = self.char1.quests.add(OakwrightTimberQuest)
        quest.status = "completed"

        result = self.call(CmdNPCQuest(), "", obj=self.oakwright)
        self.assertIn("Good wood", result)


class TestOakwrightTimberNotRepeatable(EvenniaCommandTest):
    """Test quest cannot be re-accepted after completion."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def test_cannot_reaccept(self):
        """Completed quest cannot be re-accepted."""
        quest = self.char1.quests.add(OakwrightTimberQuest)
        quest.status = "completed"

        can_accept, reason = OakwrightTimberQuest.can_accept(self.char1)
        self.assertFalse(can_accept)


class TestOakwrightTimberAbandon(EvenniaCommandTest):
    """Test quest abandon and re-accept."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.oakwright = create_object(
            OakwrightNPC, key="Master Oakwright", location=self.room1
        )
        self.oakwright.quest_key = "oakwright_timber"
        self.oakwright.trainable_skills = ["carpentry"]
        self.oakwright.trainer_masteries = {"carpentry": 2}

    def tearDown(self):
        if self.oakwright and self.oakwright.pk:
            self.oakwright.delete()
        super().tearDown()

    def test_abandon_quest(self):
        """quest abandon removes the quest."""
        self.char1.quests.add(OakwrightTimberQuest)
        result = self.call(CmdNPCQuest(), "abandon", obj=self.oakwright)
        self.assertIn("abandoned", result.lower())
        self.assertFalse(self.char1.quests.has("oakwright_timber"))


class TestOakwrightQuestContext(EvenniaCommandTest):
    """Test OakwrightNPC quest-aware context injection."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.oakwright = create_object(
            OakwrightNPC, key="Master Oakwright", location=self.room1
        )
        self.oakwright.quest_key = "oakwright_timber"
        self.oakwright.trainable_skills = ["carpentry"]
        self.oakwright.trainer_masteries = {"carpentry": 2}

    def tearDown(self):
        if self.oakwright and self.oakwright.pk:
            self.oakwright.delete()
        super().tearDown()

    def test_new_player_gets_quest_pitch(self):
        """Player with no quest gets QUEST_PITCH_CONTEXT."""
        result = self.oakwright._build_quest_context(self.char1)
        self.assertIs(result, QUEST_PITCH_CONTEXT)

    def test_level_gate(self):
        """Player at level >= 3 always gets GENERIC_CONTEXT."""
        self.char1.level = 5
        result = self.oakwright._build_quest_context(self.char1)
        self.assertIs(result, GENERIC_CONTEXT)

    def test_level_2_gets_quest_pitch(self):
        """Player at level 2 (below cap) still gets quest pitch."""
        self.char1.level = 2
        result = self.oakwright._build_quest_context(self.char1)
        self.assertIs(result, QUEST_PITCH_CONTEXT)

    def test_quest_done_gets_respect(self):
        """Player who completed timber quest gets QUEST_DONE_CONTEXT."""
        from unittest.mock import MagicMock, patch

        mock_quests = MagicMock()
        mock_quests.has.return_value = True
        mock_quests.is_completed.return_value = True
        with patch.object(type(self.char1), "quests", new_callable=lambda: property(lambda s: mock_quests)):
            result = self.oakwright._build_quest_context(self.char1)
        self.assertIs(result, QUEST_DONE_CONTEXT)

    def test_quest_active_gets_encouragement(self):
        """Player with active timber quest gets QUEST_ACTIVE_CONTEXT."""
        from unittest.mock import MagicMock, patch

        mock_quests = MagicMock()
        mock_quests.has.return_value = True
        mock_quests.is_completed.return_value = False
        with patch.object(type(self.char1), "quests", new_callable=lambda: property(lambda s: mock_quests)):
            result = self.oakwright._build_quest_context(self.char1)
        self.assertIs(result, QUEST_ACTIVE_CONTEXT)

    def test_level_gate_overrides_quest_state(self):
        """Even with active quest, level >= 3 gets GENERIC_CONTEXT."""
        from unittest.mock import MagicMock, patch

        self.char1.level = 3
        mock_quests = MagicMock()
        mock_quests.has.return_value = True
        mock_quests.is_completed.return_value = False
        with patch.object(type(self.char1), "quests", new_callable=lambda: property(lambda s: mock_quests)):
            result = self.oakwright._build_quest_context(self.char1)
        self.assertIs(result, GENERIC_CONTEXT)

    def test_has_trainer_cmdset(self):
        """OakwrightNPC should have TrainerCmdSet."""
        cmdset_keys = [cs.key for cs in self.oakwright.cmdset.all()]
        self.assertIn("TrainerCmdSet", cmdset_keys)

    def test_train_commands_in_context(self):
        """Context variables should include train_commands."""
        self.oakwright.ndb._llm_current_speaker = self.char1
        context = self.oakwright._get_context_variables()
        self.assertIn("train_commands", context)
        self.assertIn("TRAINING COMMANDS", context["train_commands"])

    def test_train_commands_lists_skills(self):
        """train_commands should list what this trainer teaches."""
        commands_text = self.oakwright._build_train_commands()
        self.assertIn("Carpentry", commands_text)
