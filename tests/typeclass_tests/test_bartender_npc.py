"""
Tests for BartenderNPC quest-aware context injection.

Covers: state detection, level gate, quest context selection,
template variable injection.

evennia test --settings settings tests.typeclass_tests.test_bartender_npc
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.actors.npcs.bartender_npc import (
    BartenderNPC,
    GENERIC_CONTEXT,
    NEW_PLAYER_CONTEXT,
    QUEST_ACTIVE_CONTEXT,
    QUEST_PITCH_CONTEXT,
    TUTORIAL_SUGGEST_CONTEXT,
)


class TestBartenderQuestContext(EvenniaCommandTest):
    """Test _build_quest_context() returns correct context per state."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bartender = create_object(
            BartenderNPC,
            key="Rowan",
            location=self.room1,
        )
        self.bartender.quest_key = "rat_cellar"

    def tearDown(self):
        if self.bartender and self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def test_new_player_context(self):
        """Brand new player (no tutorial, no quest) gets NEW_PLAYER_CONTEXT."""
        # Ensure no tutorial flag
        if self.char1.account:
            self.char1.account.db.tutorial_starter_given = False
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, NEW_PLAYER_CONTEXT)

    def test_tutorial_done_no_quest(self):
        """Player who completed tutorial but no quest gets QUEST_PITCH_CONTEXT."""
        self.char1.account.db.tutorial_starter_given = True
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, QUEST_PITCH_CONTEXT)

    def test_quest_active(self):
        """Player with active rat_cellar quest gets QUEST_ACTIVE_CONTEXT."""
        from world.quests.rat_cellar import RatCellarQuest

        self.char1.quests.add(RatCellarQuest)
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, QUEST_ACTIVE_CONTEXT)

    def test_quest_done_no_tutorial(self):
        """Player who finished quest but skipped tutorial gets TUTORIAL_SUGGEST."""
        from world.quests.rat_cellar import RatCellarQuest

        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"
        if self.char1.account:
            self.char1.account.db.tutorial_starter_given = False
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, TUTORIAL_SUGGEST_CONTEXT)

    def test_both_done(self):
        """Player who finished both tutorial and quest gets GENERIC_CONTEXT."""
        from world.quests.rat_cellar import RatCellarQuest

        quest = self.char1.quests.add(RatCellarQuest)
        quest.status = "completed"
        self.char1.account.db.tutorial_starter_given = True
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, GENERIC_CONTEXT)

    def test_level_gate(self):
        """Player at level >= 3 always gets GENERIC_CONTEXT."""
        self.char1.level = 5
        if self.char1.account:
            self.char1.account.db.tutorial_starter_given = False
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, GENERIC_CONTEXT)

    def test_level_gate_with_active_quest(self):
        """Even with active quest, level >= 3 gets GENERIC_CONTEXT."""
        from world.quests.rat_cellar import RatCellarQuest

        self.char1.level = 3
        self.char1.quests.add(RatCellarQuest)
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, GENERIC_CONTEXT)

    def test_level_2_still_gets_quest_context(self):
        """Player at level 2 (below cap) still gets state-specific context."""
        self.char1.level = 2
        if self.char1.account:
            self.char1.account.db.tutorial_starter_given = False
        result = self.bartender._build_quest_context(self.char1)
        self.assertIs(result, NEW_PLAYER_CONTEXT)


class TestBartenderContextVariables(EvenniaCommandTest):
    """Test _get_context_variables() includes quest_context."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.bartender = create_object(
            BartenderNPC,
            key="Rowan",
            location=self.room1,
        )
        self.bartender.quest_key = "rat_cellar"

    def tearDown(self):
        if self.bartender and self.bartender.pk:
            self.bartender.delete()
        super().tearDown()

    def test_quest_context_in_variables_with_speaker(self):
        """quest_context should be populated when speaker is set."""
        self.bartender.ndb._llm_current_speaker = self.char1
        context = self.bartender._get_context_variables()
        self.assertIn("quest_context", context)
        self.assertNotEqual(context["quest_context"], "")

    def test_quest_context_without_speaker(self):
        """quest_context should be GENERIC_CONTEXT when no speaker."""
        self.bartender.ndb._llm_current_speaker = None
        context = self.bartender._get_context_variables()
        self.assertIn("quest_context", context)
        self.assertIs(context["quest_context"], GENERIC_CONTEXT)

    def test_prompt_renders_with_quest_context(self):
        """The bartender.md template should render with quest_context."""
        self.bartender.ndb._llm_current_speaker = self.char1
        prompt = self.bartender.get_llm_system_prompt()
        # Should contain content from the quest context block
        self.assertIn("What you know:", prompt)
        self.assertIn("Harvest Moon Inn", prompt)
