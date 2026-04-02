"""Tests for SpawnService orchestrator."""

from decimal import Decimal
from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.service import (
    SpawnService,
    get_spawn_service,
    set_spawn_service,
)

_MINI_CONFIG = {
    ("resource", 1): {
        "calculator": "resource",
        "default_spawn_rate": 10,
        "target_price_low": 8,
        "target_price_high": 16,
        "modifier_min": 0.25,
        "modifier_max": 2.0,
    },
    ("gold", "gold"): {
        "calculator": "gold",
        "default_spawn_rate": 50,
        "buffer": 1.15,
        "min_runway_days": 7,
    },
}


class TestSpawnServiceInit(EvenniaTest):

    def create_script(self):
        pass

    def test_creates_calculators(self):
        """SpawnService creates calculator instances."""
        svc = SpawnService(_MINI_CONFIG)
        self.assertIn("resource", svc._calculators)
        self.assertIn("gold", svc._calculators)
        self.assertIn("knowledge", svc._calculators)

    def test_creates_distributors(self):
        """SpawnService creates distributor instances."""
        svc = SpawnService(_MINI_CONFIG)
        self.assertIn("resource", svc._distributors)
        self.assertIn("gold", svc._distributors)
        self.assertIn("scroll", svc._distributors)
        self.assertIn("recipe", svc._distributors)
        self.assertIn("rare_nft", svc._distributors)


class TestSpawnServiceQuestDebt(EvenniaTest):

    def create_script(self):
        pass

    def test_allocate_quest_reward_resources(self):
        """allocate_quest_reward registers debt for resources."""
        svc = SpawnService(_MINI_CONFIG)
        result = svc.allocate_quest_reward("resources", "1", 10)
        self.assertTrue(result)
        bs = svc.budget_states[("resource", 1)]
        self.assertEqual(bs.quest_debt, 10)

    def test_allocate_quest_reward_gold(self):
        """allocate_quest_reward registers debt for gold."""
        svc = SpawnService(_MINI_CONFIG)
        result = svc.allocate_quest_reward("gold", "gold", 5)
        self.assertTrue(result)
        bs = svc.budget_states[("gold", "gold")]
        self.assertEqual(bs.quest_debt, 5)

    def test_quest_debt_accumulates(self):
        """Multiple quest rewards accumulate debt."""
        svc = SpawnService(_MINI_CONFIG)
        svc.allocate_quest_reward("gold", "gold", 5)
        svc.allocate_quest_reward("gold", "gold", 3)
        bs = svc.budget_states[("gold", "gold")]
        self.assertEqual(bs.quest_debt, 8)

    def test_quest_debt_isolation(self):
        """Gold debt doesn't affect resource budget."""
        svc = SpawnService(_MINI_CONFIG)
        svc.allocate_quest_reward("gold", "gold", 5)
        svc.allocate_quest_reward("resources", "1", 3)

        gold_bs = svc.budget_states[("gold", "gold")]
        res_bs = svc.budget_states[("resource", 1)]
        self.assertEqual(gold_bs.quest_debt, 5)
        self.assertEqual(res_bs.quest_debt, 3)

    def test_quest_debt_creates_budget_state(self):
        """Quest debt creates a new BudgetState if none exists."""
        svc = SpawnService(_MINI_CONFIG)
        self.assertNotIn(("resource", 1), svc.budget_states)
        svc.allocate_quest_reward("resources", "1", 10)
        self.assertIn(("resource", 1), svc.budget_states)


class TestSpawnServiceSingleton(EvenniaTest):

    def create_script(self):
        pass

    def test_get_spawn_service_default_none(self):
        """get_spawn_service returns None before set."""
        set_spawn_service(None)
        self.assertIsNone(get_spawn_service())

    def test_set_and_get(self):
        """set_spawn_service + get_spawn_service round-trip."""
        svc = SpawnService(_MINI_CONFIG)
        set_spawn_service(svc)
        self.assertIs(get_spawn_service(), svc)
        # Clean up
        set_spawn_service(None)


class TestSpawnServiceDistributorRouting(EvenniaTest):

    def create_script(self):
        pass

    def test_resource_routes_to_resource_distributor(self):
        """resource items route to ResourceDistributor."""
        svc = SpawnService(_MINI_CONFIG)
        dist = svc._get_distributor("resource", 1)
        from blockchain.xrpl.services.spawn.distributors.fungible import ResourceDistributor
        self.assertIsInstance(dist, ResourceDistributor)

    def test_gold_routes_to_gold_distributor(self):
        """gold routes to GoldDistributor."""
        svc = SpawnService(_MINI_CONFIG)
        dist = svc._get_distributor("gold", "gold")
        from blockchain.xrpl.services.spawn.distributors.fungible import GoldDistributor
        self.assertIsInstance(dist, GoldDistributor)

    def test_knowledge_scroll_routes_to_scroll_distributor(self):
        """knowledge scroll items route to ScrollDistributor."""
        svc = SpawnService(_MINI_CONFIG)
        dist = svc._get_distributor("knowledge", "scroll_magic_missile")
        from blockchain.xrpl.services.spawn.distributors.nft import ScrollDistributor
        self.assertIsInstance(dist, ScrollDistributor)

    def test_knowledge_recipe_routes_to_recipe_distributor(self):
        """knowledge recipe items route to RecipeDistributor."""
        svc = SpawnService(_MINI_CONFIG)
        dist = svc._get_distributor("knowledge", "recipe_iron_ingot")
        from blockchain.xrpl.services.spawn.distributors.nft import RecipeDistributor
        self.assertIsInstance(dist, RecipeDistributor)

    def test_rare_nft_routes_to_rare_distributor(self):
        """rare_nft items route to RareNFTDistributor."""
        svc = SpawnService(_MINI_CONFIG)
        dist = svc._get_distributor("rare_nft", "UniqueWeapon.jupiters_lightning")
        from blockchain.xrpl.services.spawn.distributors.nft import RareNFTDistributor
        self.assertIsInstance(dist, RareNFTDistributor)

    def test_unknown_type_returns_none(self):
        """Unknown item_type returns None."""
        svc = SpawnService(_MINI_CONFIG)
        dist = svc._get_distributor("unknown", "foo")
        self.assertIsNone(dist)


class TestResolveCategoryKey(EvenniaTest):
    """Tests for SpawnService._resolve_category_key()."""

    def create_script(self):
        pass

    def test_resources_maps_to_resource_int(self):
        """'resources' category maps key to ('resource', int)."""
        item_type, type_key = SpawnService._resolve_category_key("resources", "1")
        self.assertEqual(item_type, "resource")
        self.assertEqual(type_key, 1)
        self.assertIsInstance(type_key, int)

    def test_gold_maps_to_gold_gold(self):
        """'gold' category always maps to ('gold', 'gold')."""
        item_type, type_key = SpawnService._resolve_category_key("gold", "gold")
        self.assertEqual((item_type, type_key), ("gold", "gold"))

    def test_scrolls_maps_to_knowledge(self):
        """'scrolls' category maps to ('knowledge', key)."""
        item_type, type_key = SpawnService._resolve_category_key(
            "scrolls", "scroll_magic_missile",
        )
        self.assertEqual((item_type, type_key), ("knowledge", "scroll_magic_missile"))

    def test_recipes_maps_to_knowledge(self):
        """'recipes' category maps to ('knowledge', key)."""
        item_type, type_key = SpawnService._resolve_category_key(
            "recipes", "recipe_iron_sword",
        )
        self.assertEqual((item_type, type_key), ("knowledge", "recipe_iron_sword"))

    def test_nfts_maps_to_rare_nft(self):
        """'nfts' category maps to ('rare_nft', key)."""
        item_type, type_key = SpawnService._resolve_category_key(
            "nfts", "UniqueWeapon.jupiters_lightning",
        )
        self.assertEqual(
            (item_type, type_key),
            ("rare_nft", "UniqueWeapon.jupiters_lightning"),
        )

    def test_unknown_category_passes_through(self):
        """Unknown category passes through unchanged."""
        item_type, type_key = SpawnService._resolve_category_key("other", "foo")
        self.assertEqual((item_type, type_key), ("other", "foo"))
