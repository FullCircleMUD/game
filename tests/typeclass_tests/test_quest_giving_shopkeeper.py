"""
Tests for LLMShopkeeperNPC, QuestGivingShopkeeper, and BakerNPC.

Covers: shop command injection, quest context selection, level gate,
template variable injection, shopkeeper cmdset presence.

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
from typeclasses.actors.npcs.llm_shopkeeper_npc import LLMShopkeeperNPC
from typeclasses.actors.npcs.quest_giving_shopkeeper import (
    QuestGivingShopkeeper,
)


# ══════════════════════════════════════════════════════════════════════════
#  LLMShopkeeperNPC (shop only, no quest infrastructure)
# ══════════════════════════════════════════════════════════════════════════

class TestLLMShopkeeperNPC(EvenniaCommandTest):
    """Test the LLMShopkeeperNPC typeclass — shop without quests."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.npc = create_object(
            LLMShopkeeperNPC,
            key="TestLLMShopkeeper",
            location=self.room1,
        )

    def tearDown(self):
        if self.npc and self.npc.pk:
            self.npc.delete()
        super().tearDown()

    def test_has_shopkeeper_cmdset(self):
        """ShopkeeperCmdSet should be attached on creation."""
        cmdset_keys = [cs.key for cs in self.npc.cmdset.all()]
        self.assertIn("ShopkeeperCmdSet", cmdset_keys)

    def test_has_shop_name_attribute(self):
        """shop_name should be accessible as a property (not just db)."""
        self.assertEqual(self.npc.shop_name, "Shop")
        self.npc.shop_name = "Test Shop"
        self.assertEqual(self.npc.shop_name, "Test Shop")

    def test_has_tradeable_resources_attribute(self):
        """tradeable_resources should be accessible as a property."""
        self.assertEqual(self.npc.tradeable_resources, [])
        self.npc.tradeable_resources = [6, 7]
        self.assertEqual(self.npc.tradeable_resources, [6, 7])

    def test_shop_commands_in_context(self):
        """Context variables should include shop_commands."""
        context = self.npc._get_context_variables()
        self.assertIn("shop_commands", context)
        self.assertIn("SHOP COMMANDS", context["shop_commands"])

    def test_no_quest_context_in_variables(self):
        """LLMShopkeeperNPC should NOT have quest_context in variables."""
        context = self.npc._get_context_variables()
        self.assertNotIn("quest_context", context)

    def test_no_quest_giver_mixin(self):
        """LLMShopkeeperNPC should not have QuestGiverMixin methods."""
        self.assertFalse(hasattr(self.npc, "quest_key"))

    def test_vector_memory_disabled_by_default(self):
        """Should default to no vector memory."""
        self.assertFalse(self.npc.llm_use_vector_memory)

    def test_shop_commands_lists_tradeable(self):
        """shop_commands should list what the shop trades."""
        self.npc.tradeable_resources = [6, 7]  # Wood, Timber
        text = self.npc._build_shop_commands()
        self.assertIn("Wood", text)
        self.assertIn("Timber", text)

    def test_shop_commands_empty_stock(self):
        """shop_commands with no tradeable resources says nothing to trade."""
        self.npc.tradeable_resources = []
        text = self.npc._build_shop_commands()
        self.assertIn("nothing to trade", text)


# ══════════════════════════════════════════════════════════════════════════
#  QuestGivingShopkeeper (shop + quest)
# ══════════════════════════════════════════════════════════════════════════

class TestQuestGivingShopkeeper(EvenniaCommandTest):
    """Test the generic QuestGivingShopkeeper typeclass."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.shopkeeper = create_object(
            QuestGivingShopkeeper,
            key="TestShopkeeper",
            location=self.room1,
        )

    def tearDown(self):
        if self.shopkeeper and self.shopkeeper.pk:
            self.shopkeeper.delete()
        super().tearDown()

    def test_has_shopkeeper_cmdset(self):
        """ShopkeeperCmdSet should be attached on creation."""
        cmdset_keys = [cs.key for cs in self.shopkeeper.cmdset.all()]
        self.assertIn("ShopkeeperCmdSet", cmdset_keys)

    def test_shop_commands_in_context(self):
        """Context variables should include shop_commands."""
        self.shopkeeper.ndb._llm_current_speaker = self.char1
        context = self.shopkeeper._get_context_variables()
        self.assertIn("shop_commands", context)
        self.assertIn("SHOP COMMANDS", context["shop_commands"])

    def test_shop_commands_lists_commands(self):
        """shop_commands should contain all command syntaxes."""
        commands_text = self.shopkeeper._build_shop_commands()
        self.assertIn("list", commands_text)
        self.assertIn("buy", commands_text)
        self.assertIn("sell", commands_text)
        self.assertIn("quote buy", commands_text)
        self.assertIn("quote sell", commands_text)
        self.assertIn("accept", commands_text)

    def test_shop_commands_shows_tradeable_resources(self):
        """shop_commands should list what the shop trades."""
        self.shopkeeper.tradeable_resources = [2, 3]  # Flour, Bread
        commands_text = self.shopkeeper._build_shop_commands()
        self.assertIn("Flour", commands_text)
        self.assertIn("Bread", commands_text)

    def test_shop_commands_empty_stock(self):
        """shop_commands with no tradeable resources says nothing to trade."""
        self.shopkeeper.tradeable_resources = []
        commands_text = self.shopkeeper._build_shop_commands()
        self.assertIn("nothing to trade", commands_text)

    def test_default_quest_context_empty(self):
        """Default _build_quest_context returns empty string."""
        result = self.shopkeeper._build_quest_context(self.char1)
        self.assertEqual(result, "")

    def test_quest_context_in_variables_with_speaker(self):
        """quest_context should be populated when speaker is set."""
        self.shopkeeper.ndb._llm_current_speaker = self.char1
        context = self.shopkeeper._get_context_variables()
        self.assertIn("quest_context", context)

    def test_quest_context_without_speaker(self):
        """quest_context should be empty string when no speaker."""
        self.shopkeeper.ndb._llm_current_speaker = None
        context = self.shopkeeper._get_context_variables()
        self.assertIn("quest_context", context)
        self.assertEqual(context["quest_context"], "")

    def test_vector_memory_disabled_by_default(self):
        """QuestGivingShopkeeper should default to no vector memory."""
        self.assertFalse(self.shopkeeper.llm_use_vector_memory)


class TestBakerNPC(EvenniaCommandTest):
    """Test BakerNPC quest-aware context injection."""

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
        self.baker.tradeable_resources = [2, 3]
        self.baker.shop_name = "Goldencrust Bakery"

    def tearDown(self):
        if self.baker and self.baker.pk:
            self.baker.delete()
        super().tearDown()

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

    def test_has_shopkeeper_cmdset(self):
        """BakerNPC should have ShopkeeperCmdSet."""
        cmdset_keys = [cs.key for cs in self.baker.cmdset.all()]
        self.assertIn("ShopkeeperCmdSet", cmdset_keys)

    def test_prompt_renders(self):
        """The baker.md template should render without errors."""
        self.baker.llm_prompt_file = "baker.md"
        self.baker.ndb._llm_current_speaker = self.char1
        prompt = self.baker.get_llm_system_prompt()
        self.assertIn("Bron", prompt)
        self.assertIn("SHOP COMMANDS", prompt)
