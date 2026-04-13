"""
Architecture tests for the shopkeeper NPC hierarchy.

Covers the layers introduced by the shopkeeper refactor that don't have
direct tests elsewhere:

- ShopkeeperNPC abstract contract (NotImplementedError for each method)
- LLMQuestContextMixin isolation (injection behaviour without other classes)
- LLMTrainerNPC (extracted from old QuestGivingLLMTrainer)
- NFTShopkeeperNPC basics (pre-existing gap filled)
- LLMNFTShopkeeperNPC basics
- Smoke test for every reparented multi-role NPC — verifies MRO chains
  resolve cleanly and the expected cmdsets are attached at creation time

evennia test --settings settings tests.typeclass_tests.test_shopkeeper_architecture
"""

import unittest
from unittest.mock import MagicMock

from evennia import create_object
from evennia.utils.test_resources import EvenniaCommandTest

from typeclasses.actors.npcs.llm_nft_shopkeeper import LLMNFTShopkeeperNPC
from typeclasses.actors.npcs.llm_resource_shopkeeper import LLMResourceShopkeeperNPC
from typeclasses.actors.npcs.llm_trainer import LLMTrainerNPC
from typeclasses.actors.npcs.nft_shopkeeper import NFTShopkeeperNPC
from typeclasses.actors.npcs.resource_shopkeeper import ResourceShopkeeperNPC
from typeclasses.actors.npcs.shopkeeper import ShopkeeperNPC
from typeclasses.mixins.llm_quest_context import LLMQuestContextMixin


# ══════════════════════════════════════════════════════════════════════════
#  ShopkeeperNPC — abstract contract
# ══════════════════════════════════════════════════════════════════════════


class TestShopkeeperAbstractContract(EvenniaCommandTest):
    """The abstract base must raise NotImplementedError for each method."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.npc = create_object(
            ShopkeeperNPC, key="AbstractShop", location=self.room1,
        )

    def tearDown(self):
        if self.npc and self.npc.pk:
            self.npc.delete()
        super().tearDown()

    def test_get_buy_price_raises(self):
        with self.assertRaises(NotImplementedError):
            self.npc.get_buy_price("anything", 1)

    def test_get_sell_price_raises(self):
        with self.assertRaises(NotImplementedError):
            self.npc.get_sell_price("anything", 1)

    def test_execute_buy_raises(self):
        with self.assertRaises(NotImplementedError):
            self.npc.execute_buy(self.char1, {"direction": "buy"})

    def test_execute_sell_raises(self):
        with self.assertRaises(NotImplementedError):
            self.npc.execute_sell(self.char1, {"direction": "sell"})

    def test_list_inventory_raises(self):
        with self.assertRaises(NotImplementedError):
            self.npc.list_inventory()

    def test_quote_hint_raises(self):
        with self.assertRaises(NotImplementedError):
            self.npc.quote_hint()

    def test_has_shop_name_and_inventory_attributes(self):
        """The contract attributes should exist with sane defaults."""
        self.assertEqual(self.npc.shop_name, "Shop")
        self.assertEqual(self.npc.inventory, [])


# ══════════════════════════════════════════════════════════════════════════
#  LLMQuestContextMixin — isolated unit test
# ══════════════════════════════════════════════════════════════════════════


class _FakeBase:
    """Stand-in for the LLMMixin's _get_context_variables() contract."""

    def _get_context_variables(self):
        return {"base_key": "base_value"}


class _FakeQuestNPC(LLMQuestContextMixin, _FakeBase):
    """Minimal concrete class to exercise the mixin without DB plumbing."""

    def __init__(self):
        self.ndb = MagicMock()
        self.ndb._llm_current_speaker = None

    def _build_quest_context(self, character):
        return f"quest context for {character}"


class TestLLMQuestContextMixin(unittest.TestCase):
    """Unit-tests the mixin in isolation — no Evennia typeclass involved."""

    def test_base_context_preserved(self):
        """Mixin must cooperatively chain super() and preserve base keys."""
        npc = _FakeQuestNPC()
        context = npc._get_context_variables()
        self.assertEqual(context["base_key"], "base_value")

    def test_quest_context_empty_when_no_speaker(self):
        """No speaker on ndb → quest_context is empty string."""
        npc = _FakeQuestNPC()
        npc.ndb._llm_current_speaker = None
        context = npc._get_context_variables()
        self.assertIn("quest_context", context)
        self.assertEqual(context["quest_context"], "")

    def test_quest_context_calls_build_when_speaker(self):
        """With a speaker, _build_quest_context is called with that speaker."""
        npc = _FakeQuestNPC()
        npc.ndb._llm_current_speaker = "test_player"
        context = npc._get_context_variables()
        self.assertEqual(context["quest_context"], "quest context for test_player")

    def test_default_build_returns_empty_string(self):
        """The default _build_quest_context hook returns empty string."""

        class _DefaultNPC(LLMQuestContextMixin, _FakeBase):
            def __init__(self):
                self.ndb = MagicMock()
                self.ndb._llm_current_speaker = "player"

        npc = _DefaultNPC()
        self.assertEqual(npc._build_quest_context("anything"), "")


# ══════════════════════════════════════════════════════════════════════════
#  LLMTrainerNPC — extracted from old QuestGivingLLMTrainer
# ══════════════════════════════════════════════════════════════════════════


class TestLLMTrainerNPC(EvenniaCommandTest):
    """LLM trainer without any quest infrastructure."""

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.npc = create_object(
            LLMTrainerNPC, key="Bob the Trainer", location=self.room1,
        )
        self.npc.trainable_skills = ["carpentry"]
        self.npc.trainer_masteries = {"carpentry": 2}

    def tearDown(self):
        if self.npc and self.npc.pk:
            self.npc.delete()
        super().tearDown()

    def test_has_trainer_cmdset(self):
        """TrainerCmdSet should be attached via TrainerNPC.at_object_creation."""
        cmdset_keys = [cs.key for cs in self.npc.cmdset.all()]
        self.assertIn("TrainerCmdSet", cmdset_keys)

    def test_train_commands_in_context(self):
        """Context variables should include {train_commands}."""
        context = self.npc._get_context_variables()
        self.assertIn("train_commands", context)
        self.assertIn("TRAINING COMMANDS", context["train_commands"])

    def test_no_quest_context_without_mixin(self):
        """Plain LLMTrainerNPC (no quest mixin) has no quest_context."""
        context = self.npc._get_context_variables()
        self.assertNotIn("quest_context", context)

    def test_train_commands_lists_skills(self):
        """Train commands block should list the NPC's skills."""
        text = self.npc._build_train_commands()
        self.assertIn("Carpentry", text)


# ══════════════════════════════════════════════════════════════════════════
#  NFTShopkeeperNPC — fills pre-existing coverage gap
# ══════════════════════════════════════════════════════════════════════════


class TestNFTShopkeeperNPC(EvenniaCommandTest):
    """Basic creation + attribute + cmdset tests for the NFT shopkeeper."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.npc = create_object(
            NFTShopkeeperNPC, key="Grik", location=self.room1,
        )
        self.npc.shop_name = "Blades & Blunts"
        self.npc.inventory = ["Training Dagger", "Training Shortsword"]

    def tearDown(self):
        if self.npc and self.npc.pk:
            self.npc.delete()
        super().tearDown()

    def test_has_nft_shop_cmdset(self):
        """NFTShopCmdSet should be attached on creation."""
        cmdset_keys = [cs.key for cs in self.npc.cmdset.all()]
        self.assertIn("NFTShopCmdSet", cmdset_keys)

    def test_inventory_is_str_list(self):
        """NFT inventory atoms are NFTItemType name strings."""
        self.assertEqual(
            self.npc.inventory, ["Training Dagger", "Training Shortsword"]
        )

    def test_shop_name_roundtrips(self):
        self.assertEqual(self.npc.shop_name, "Blades & Blunts")

    def test_quote_hint_differs_from_resource(self):
        """NFT quote hint uses NFT grammar (no <amount>)."""
        hint = self.npc.quote_hint()
        self.assertIn("quote buy <item>", hint)
        self.assertNotIn("<amount>", hint)

    def test_execute_buy_rejects_non_singleton(self):
        """NFT shops must reject qty != 1 even if it slips through."""
        with self.assertRaises(AssertionError):
            self.npc.execute_buy(self.char1, {"qty": 2})

    def test_execute_sell_rejects_non_singleton(self):
        with self.assertRaises(AssertionError):
            self.npc.execute_sell(self.char1, {"qty": 2})


# ══════════════════════════════════════════════════════════════════════════
#  LLMNFTShopkeeperNPC — symmetry with LLMResourceShopkeeperNPC
# ══════════════════════════════════════════════════════════════════════════


class TestLLMNFTShopkeeperNPC(EvenniaCommandTest):
    """LLM-powered NFT shopkeeper."""

    databases = "__all__"

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.npc = create_object(
            LLMNFTShopkeeperNPC, key="TestLLMNFTShop", location=self.room1,
        )

    def tearDown(self):
        if self.npc and self.npc.pk:
            self.npc.delete()
        super().tearDown()

    def test_has_nft_shop_cmdset(self):
        cmdset_keys = [cs.key for cs in self.npc.cmdset.all()]
        self.assertIn("NFTShopCmdSet", cmdset_keys)

    def test_shop_commands_in_context(self):
        context = self.npc._get_context_variables()
        self.assertIn("shop_commands", context)
        self.assertIn("SHOP COMMANDS", context["shop_commands"])

    def test_shop_commands_uses_nft_grammar(self):
        """Shop commands block must use NFT grammar (no <amount>)."""
        text = self.npc._build_shop_commands()
        self.assertIn("quote buy <item>", text)
        self.assertNotIn("<amount>", text)

    def test_no_quest_context_by_default(self):
        """Plain LLM NFT shop has no quest mixin → no quest_context key."""
        context = self.npc._get_context_variables()
        self.assertNotIn("quest_context", context)


# ══════════════════════════════════════════════════════════════════════════
#  MRO / cmdset smoke tests for every reparented multi-role NPC
# ══════════════════════════════════════════════════════════════════════════


class TestReparentedNPCSmoke(EvenniaCommandTest):
    """Verify every reparented multi-role NPC instantiates and composes correctly.

    Catches MRO / at_object_creation chain failures that wouldn't surface
    until the first time the NPC is spawned in the live game.
    """

    character_typeclass = "typeclasses.actors.character.FCMCharacter"
    databases = "__all__"

    def create_script(self):
        pass

    def _assert_cmdset(self, npc, cmdset_key):
        cmdset_keys = [cs.key for cs in npc.cmdset.all()]
        self.assertIn(cmdset_key, cmdset_keys)

    def test_oakwright_creates(self):
        from typeclasses.actors.npcs.oakwright_npc import OakwrightNPC
        npc = create_object(OakwrightNPC, key="Oakwright", location=self.room1)
        self._assert_cmdset(npc, "TrainerCmdSet")
        self._assert_cmdset(npc, "QuestGiverCmdSet")
        npc.delete()

    def test_torben_creates(self):
        from typeclasses.actors.npcs.torben_npc import TorbenNPC
        npc = create_object(TorbenNPC, key="Torben", location=self.room1)
        self._assert_cmdset(npc, "TrainerCmdSet")
        npc.delete()

    def test_hendricks_creates(self):
        from typeclasses.actors.npcs.hendricks_npc import HendricksNPC
        npc = create_object(HendricksNPC, key="Hendricks", location=self.room1)
        self._assert_cmdset(npc, "TrainerCmdSet")
        self._assert_cmdset(npc, "QuestGiverCmdSet")
        npc.delete()

    def test_elena_creates(self):
        from typeclasses.actors.npcs.elena_npc import ElenaNPC
        npc = create_object(ElenaNPC, key="Elena", location=self.room1)
        self._assert_cmdset(npc, "TrainerCmdSet")
        self._assert_cmdset(npc, "QuestGiverCmdSet")
        npc.delete()

    def test_mara_creates_with_four_way_composition(self):
        """Mara is the wedge case: LLM + quest + shop + trainer at once.

        If any MRO chain is broken, this test fails at create_object time.
        """
        from typeclasses.actors.npcs.mara_npc import MaraNPC
        npc = create_object(MaraNPC, key="Mara", location=self.room1)
        self._assert_cmdset(npc, "ResourceShopCmdSet")
        self._assert_cmdset(npc, "TrainerCmdSet")
        self._assert_cmdset(npc, "QuestGiverCmdSet")
        # Shop attrs must be present on the typeclass, not just spawn-script
        # plain attributes (the original Mara bug).
        self.assertEqual(npc.shop_name, "Shop")  # default; spawn script overrides
        self.assertEqual(npc.inventory, [])
        npc.delete()
