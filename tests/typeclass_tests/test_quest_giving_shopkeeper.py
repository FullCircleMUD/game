"""
Tests for LLMResourceShopkeeperNPC and BakerNPC.

Covers: shop command injection, quest context selection, level gate,
template variable injection, shopkeeper cmdset presence, and the new
explicit composition of BakerNPC (LLMQuestContextMixin + QuestGiverMixin
+ LLMResourceShopkeeperNPC).

evennia test --settings settings tests.typeclass_tests.test_quest_giving_shopkeeper
"""

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.actors.npcs.baker_npc import (
    BakerNPC,
    GENERIC_CONTEXT,
    QUEST_ACTIVE_CONTEXT,
    QUEST_DONE_CONTEXT,
    QUEST_PITCH_CONTEXT,
)
from typeclasses.actors.npcs.llm_resource_shopkeeper import LLMResourceShopkeeperNPC


# ══════════════════════════════════════════════════════════════════════════
#  LLMResourceShopkeeperNPC (shop only, no quest infrastructure)
# ══════════════════════════════════════════════════════════════════════════


class TestLLMResourceShopkeeperNPC(EvenniaCommandTest):
    """Test the LLMResourceShopkeeperNPC typeclass — shop without quests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.npc = create_object(
            LLMResourceShopkeeperNPC,
            key="TestLLMShopkeeper",
            location=self.room1,
        )

    def tearDown(self):
        if self.npc and self.npc.pk:
            self.npc.delete()
        super().tearDown()

    def test_has_resource_shop_cmdset(self):
        """ResourceShopCmdSet should be attached on creation."""
        cmdset_keys = [cs.key for cs in self.npc.cmdset.all()]
        self.assertIn("ResourceShopCmdSet", cmdset_keys)

    def test_has_shop_name_attribute(self):
        """shop_name should be accessible as an AttributeProperty."""
        self.assertEqual(self.npc.shop_name, "Shop")
        self.npc.shop_name = "Test Shop"
        self.assertEqual(self.npc.shop_name, "Test Shop")

    def test_has_inventory_attribute(self):
        """inventory should be accessible as an AttributeProperty."""
        self.assertEqual(self.npc.inventory, [])
        self.npc.inventory = [6, 7]
        self.assertEqual(self.npc.inventory, [6, 7])

    def test_shop_commands_in_context(self):
        """Context variables should include shop_commands."""
        context = self.npc._get_context_variables()
        self.assertIn("shop_commands", context)
        self.assertIn("SHOP COMMANDS", context["shop_commands"])

    def test_no_quest_context_in_variables(self):
        """Plain LLMResourceShopkeeperNPC (no quest mixin) has no quest_context."""
        context = self.npc._get_context_variables()
        self.assertNotIn("quest_context", context)

    def test_vector_memory_disabled_by_default(self):
        """Should default to no vector memory."""
        self.assertFalse(self.npc.llm_use_vector_memory)

    def test_shop_commands_lists_tradeable(self):
        """shop_commands should list what the shop trades."""
        self.npc.inventory = [6, 7]  # Wood, Timber
        text = self.npc._build_shop_commands()
        self.assertIn("Wood", text)
        self.assertIn("Timber", text)

    def test_shop_commands_empty_stock(self):
        """shop_commands with empty inventory says nothing to trade."""
        self.npc.inventory = []
        text = self.npc._build_shop_commands()
        self.assertIn("nothing to trade", text)


# ══════════════════════════════════════════════════════════════════════════
#  BakerNPC (shop + quest + LLMQuestContextMixin)
# ══════════════════════════════════════════════════════════════════════════


class TestBakerNPC(EvenniaCommandTest):
    """Test BakerNPC quest-aware context injection and composition."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.baker = create_object(
            BakerNPC,
            key="Bron",
            location=self.room1,
        )
        self.baker.quest_key = "bakers_flour"
        self.baker.inventory = [2, 3]
        self.baker.shop_name = "Goldencrust Bakery"

    def tearDown(self):
        if self.baker and self.baker.pk:
            self.baker.delete()
        super().tearDown()

    def test_has_resource_shop_cmdset(self):
        """BakerNPC should have ResourceShopCmdSet (from LLMResourceShopkeeperNPC)."""
        cmdset_keys = [cs.key for cs in self.baker.cmdset.all()]
        self.assertIn("ResourceShopCmdSet", cmdset_keys)

    def test_shop_commands_in_context(self):
        """Context variables should include shop_commands."""
        self.baker.ndb._llm_current_speaker = self.char1
        context = self.baker._get_context_variables()
        self.assertIn("shop_commands", context)
        self.assertIn("SHOP COMMANDS", context["shop_commands"])

    def test_quest_context_in_variables_with_speaker(self):
        """quest_context should be populated via LLMQuestContextMixin when speaker is set."""
        self.baker.ndb._llm_current_speaker = self.char1
        context = self.baker._get_context_variables()
        self.assertIn("quest_context", context)

    def test_quest_context_without_speaker(self):
        """quest_context should be empty string when no speaker."""
        self.baker.ndb._llm_current_speaker = None
        context = self.baker._get_context_variables()
        self.assertIn("quest_context", context)
        self.assertEqual(context["quest_context"], "")

    def test_new_player_gets_quest_pitch(self):
        """Player with no quest gets QUEST_PITCH_CONTEXT."""
        result = self.baker._build_quest_context(self.char1)
        self.assertIs(result, QUEST_PITCH_CONTEXT)

    def test_level_gate(self):
        """Player at level >= 3 always gets GENERIC_CONTEXT."""
        self.char1.level = 5
        result = self.baker._build_quest_context(self.char1)
        self.assertIs(result, GENERIC_CONTEXT)

    def test_level_2_gets_quest_pitch(self):
        """Player at level 2 (below cap) still gets quest pitch."""
        self.char1.level = 2
        result = self.baker._build_quest_context(self.char1)
        self.assertIs(result, QUEST_PITCH_CONTEXT)

    def test_quest_done_gets_grateful(self):
        """Player who completed baker quest gets QUEST_DONE_CONTEXT."""
        from unittest.mock import MagicMock, patch

        mock_quests = MagicMock()
        mock_quests.has.return_value = True
        mock_quests.is_completed.return_value = True
        with patch.object(type(self.char1), "quests", new_callable=lambda: property(lambda s: mock_quests)):
            result = self.baker._build_quest_context(self.char1)
        self.assertIs(result, QUEST_DONE_CONTEXT)

    def test_quest_active_gets_encouragement(self):
        """Player with active baker quest gets QUEST_ACTIVE_CONTEXT."""
        from unittest.mock import MagicMock, patch

        mock_quests = MagicMock()
        mock_quests.has.return_value = True
        mock_quests.is_completed.return_value = False
        with patch.object(type(self.char1), "quests", new_callable=lambda: property(lambda s: mock_quests)):
            result = self.baker._build_quest_context(self.char1)
        self.assertIs(result, QUEST_ACTIVE_CONTEXT)

    def test_level_gate_overrides_quest_state(self):
        """Even with active quest, level >= 3 gets GENERIC_CONTEXT."""
        from unittest.mock import MagicMock, patch

        self.char1.level = 3
        mock_quests = MagicMock()
        mock_quests.has.return_value = True
        mock_quests.is_completed.return_value = False
        with patch.object(type(self.char1), "quests", new_callable=lambda: property(lambda s: mock_quests)):
            result = self.baker._build_quest_context(self.char1)
        self.assertIs(result, GENERIC_CONTEXT)

    def test_prompt_renders(self):
        """The baker.md template should render without errors."""
        self.baker.llm_prompt_file = "baker.md"
        self.baker.ndb._llm_current_speaker = self.char1
        prompt = self.baker.get_llm_system_prompt()
        self.assertIn("Bron", prompt)
        self.assertIn("SHOP COMMANDS", prompt)
