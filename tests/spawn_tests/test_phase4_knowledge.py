"""Tests for Phase 4 — knowledge item spawning (scrolls and recipes).

Covers:
  - CombatMob scroll/recipe tags on creation
  - Mob subclasses get correct builder-set tier dicts
  - Mobs without spawn_scrolls_max don't get tags
  - populate_knowledge_config() generates entries from registries
  - _resolve_nft_item_type_name() lookup
  - Zone spawn script scroll/recipe tag sync

evennia test --settings settings tests.spawn_tests.test_phase4_knowledge
"""

from unittest.mock import patch, MagicMock

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest


# ================================================================== #
#  Mob tag/attribute registration
# ================================================================== #


class TestMobScrollRecipeTags(EvenniaTest):
    """Mobs with spawn_scrolls_max/spawn_recipes_max get appropriate tags."""

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.room = create.create_object(
            "typeclasses.terrain.rooms.room_base.RoomBase",
            key="Test Room",
        )

    def test_kobold_has_scroll_tag(self):
        """Kobold (spawn_scrolls_max={"basic": 1}) gets spawn_scrolls tag."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_scrolls", return_list=True)
        self.assertIn("spawn_scrolls", tags)

    def test_kobold_has_recipe_tag(self):
        """Kobold gets spawn_recipes tag."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_recipes", return_list=True)
        self.assertIn("spawn_recipes", tags)

    def test_kobold_scrolls_max_is_basic(self):
        """Kobold gets builder-set basic tier dict."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room,
        )
        expected = {"basic": 1}
        self.assertEqual(dict(mob.db.spawn_scrolls_max), expected)

    def test_kobold_recipes_max_is_basic(self):
        """Kobold gets builder-set basic tier dict."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold.Kobold",
            key="a kobold",
            location=self.room,
        )
        expected = {"basic": 1}
        self.assertEqual(dict(mob.db.spawn_recipes_max), expected)

    def test_gnoll_has_skilled_tier(self):
        """Gnoll gets builder-set basic+skilled tier dict."""
        mob = create.create_object(
            "typeclasses.actors.mobs.gnoll.Gnoll",
            key="a gnoll",
            location=self.room,
        )
        expected = {"basic": 1, "skilled": 1}
        self.assertEqual(dict(mob.db.spawn_scrolls_max), expected)
        self.assertEqual(dict(mob.db.spawn_recipes_max), expected)

    def test_gnoll_warlord_has_expert_tier(self):
        """GnollWarlord gets builder-set basic+skilled+expert tier dict."""
        mob = create.create_object(
            "typeclasses.actors.mobs.gnoll_warlord.GnollWarlord",
            key="Gnoll Warlord",
            location=self.room,
        )
        expected = {"basic": 1, "skilled": 1, "expert": 2}
        self.assertEqual(dict(mob.db.spawn_scrolls_max), expected)
        self.assertEqual(dict(mob.db.spawn_recipes_max), expected)

    def test_kobold_chieftain_has_skilled_tier(self):
        """KoboldChieftain gets builder-set basic+skilled tier dict."""
        mob = create.create_object(
            "typeclasses.actors.mobs.kobold_chieftain.KoboldChieftain",
            key="Kobold Chieftain",
            location=self.room,
        )
        expected = {"basic": 1, "skilled": 1}
        self.assertEqual(dict(mob.db.spawn_scrolls_max), expected)

    def test_wolf_has_no_scroll_tag(self):
        """Wolf (no spawn_scrolls_max) should NOT get spawn_scrolls tag."""
        mob = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_scrolls", return_list=True)
        self.assertNotIn("spawn_scrolls", tags)

    def test_wolf_has_no_recipe_tag(self):
        """Wolf should NOT get spawn_recipes tag."""
        mob = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room,
        )
        tags = mob.tags.get(category="spawn_recipes", return_list=True)
        self.assertNotIn("spawn_recipes", tags)

    def test_wolf_has_empty_scrolls_max(self):
        """Wolf should have empty spawn_scrolls_max (no knowledge loot)."""
        mob = create.create_object(
            "typeclasses.actors.mobs.wolf.Wolf",
            key="a grey wolf",
            location=self.room,
        )
        self.assertFalse(mob.spawn_scrolls_max)

    def test_base_combat_mob_no_scroll_tag(self):
        """Base CombatMob (empty dicts) should NOT get scroll/recipe tags."""
        mob = create.create_object(
            "typeclasses.actors.mob.CombatMob",
            key="a mob",
            location=self.room,
        )
        self.assertNotIn(
            "spawn_scrolls",
            mob.tags.get(category="spawn_scrolls", return_list=True),
        )
        self.assertNotIn(
            "spawn_recipes",
            mob.tags.get(category="spawn_recipes", return_list=True),
        )


# ================================================================== #
#  populate_knowledge_config
# ================================================================== #


class TestPopulateKnowledgeConfig(EvenniaTest):

    def create_script(self):
        pass

    def test_populates_scroll_entries(self):
        """populate_knowledge_config adds scroll entries from SPELL_REGISTRY."""
        from blockchain.xrpl.services.spawn.config import populate_knowledge_config

        config = {}
        populate_knowledge_config(config)

        # Check that at least some scroll entries were added
        scroll_keys = [k for k in config if k[0] == "knowledge" and k[1].startswith("scroll_")]
        self.assertGreater(len(scroll_keys), 0, "Expected scroll entries in config")

    def test_populates_recipe_entries(self):
        """populate_knowledge_config adds recipe entries from RECIPES."""
        from blockchain.xrpl.services.spawn.config import populate_knowledge_config

        config = {}
        populate_knowledge_config(config)

        recipe_keys = [k for k in config if k[0] == "knowledge" and k[1].startswith("recipe_")]
        self.assertGreater(len(recipe_keys), 0, "Expected recipe entries in config")

    def test_scroll_entry_has_required_fields(self):
        """Each scroll entry should have calculator, base_drop_rate, tier, prototype_key."""
        from blockchain.xrpl.services.spawn.config import populate_knowledge_config

        config = {}
        populate_knowledge_config(config)

        scroll_keys = [k for k in config if k[1].startswith("scroll_")]
        self.assertGreater(len(scroll_keys), 0)

        entry = config[scroll_keys[0]]
        self.assertEqual(entry["calculator"], "knowledge")
        self.assertIn("base_drop_rate", entry)
        self.assertIn("tier", entry)
        self.assertIn("prototype_key", entry)
        self.assertIn(entry["tier"], ["basic", "skilled", "expert", "master", "gm"])

    def test_recipe_entry_has_prototype_key(self):
        """Each recipe entry should have a prototype_key ending in _recipe."""
        from blockchain.xrpl.services.spawn.config import populate_knowledge_config

        config = {}
        populate_knowledge_config(config)

        recipe_keys = [k for k in config if k[1].startswith("recipe_")]
        self.assertGreater(len(recipe_keys), 0)

        for key in recipe_keys:
            entry = config[key]
            self.assertTrue(
                entry["prototype_key"].endswith("_recipe"),
                f"Expected prototype_key ending in _recipe, got {entry['prototype_key']}",
            )

    def test_scroll_prototype_key_format(self):
        """Scroll prototype_key should be {spell_key}_scroll."""
        from blockchain.xrpl.services.spawn.config import populate_knowledge_config

        config = {}
        populate_knowledge_config(config)

        for key, entry in config.items():
            if key[1].startswith("scroll_"):
                spell_key = key[1].removeprefix("scroll_")
                self.assertEqual(
                    entry["prototype_key"],
                    f"{spell_key}_scroll",
                )

    def test_does_not_duplicate_on_second_call(self):
        """Calling populate_knowledge_config twice overwrites, not duplicates."""
        from blockchain.xrpl.services.spawn.config import populate_knowledge_config

        config = {}
        populate_knowledge_config(config)
        count_first = len(config)
        populate_knowledge_config(config)
        count_second = len(config)
        self.assertEqual(count_first, count_second)


# ================================================================== #
#  _resolve_nft_item_type_name
# ================================================================== #


class TestResolveNFTItemTypeName(EvenniaTest):
    """Test prototype_key → NFTItemType.name resolution."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_returns_none_for_unknown_type_key(self):
        """Unknown type_key returns None."""
        from blockchain.xrpl.services.spawn.distributors.nft import (
            _resolve_nft_item_type_name,
        )
        result = _resolve_nft_item_type_name("scroll_nonexistent_spell")
        self.assertIsNone(result)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", {
        ("knowledge", "scroll_test"): {"prototype_key": "test_scroll"},
    })
    def test_returns_none_when_nft_item_type_missing(self):
        """Returns None when NFTItemType doesn't exist for prototype_key."""
        from blockchain.xrpl.services.spawn.distributors.nft import (
            _resolve_nft_item_type_name,
        )
        result = _resolve_nft_item_type_name("scroll_test")
        self.assertIsNone(result)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", {
        ("knowledge", "scroll_test"): {"prototype_key": "test_scroll"},
    })
    def test_returns_name_when_item_type_exists(self):
        """Returns NFTItemType.name when the item type exists."""
        from blockchain.xrpl.models import NFTItemType
        from blockchain.xrpl.services.spawn.distributors.nft import (
            _resolve_nft_item_type_name,
        )

        NFTItemType.objects.create(
            name="Scroll of Test",
            prototype_key="test_scroll",
            typeclass="typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem",
        )

        result = _resolve_nft_item_type_name("scroll_test")
        self.assertEqual(result, "Scroll of Test")

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", {
        ("knowledge", "scroll_no_proto"): {"calculator": "knowledge"},
    })
    def test_returns_none_for_missing_prototype_key(self):
        """Config entry without prototype_key returns None."""
        from blockchain.xrpl.services.spawn.distributors.nft import (
            _resolve_nft_item_type_name,
        )
        result = _resolve_nft_item_type_name("scroll_no_proto")
        self.assertIsNone(result)
