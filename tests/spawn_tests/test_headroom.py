"""Tests for get_current_count() and count_nfts()."""

from unittest.mock import MagicMock, PropertyMock

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.headroom import (
    get_current_count,
    count_nfts,
)


def _mock_target(**db_attrs):
    """Create a mock target with db attributes."""
    target = MagicMock()
    db = MagicMock()
    for key, val in db_attrs.items():
        setattr(db, key, val)
    # Ensure hasattr checks work for missing attrs
    if "resource_count" not in db_attrs:
        del db.resource_count
    target.db = db
    target.contents = []
    return target


class TestGetCurrentCountResources(EvenniaTest):

    def create_script(self):
        pass

    def test_harvest_room_uses_resource_count(self):
        """Harvest rooms use db.resource_count, not db.resources."""
        target = _mock_target(resource_count=7)
        self.assertEqual(get_current_count(target, "resources", 1), 7)

    def test_harvest_room_zero_returns_zero(self):
        """Harvest room with resource_count=0 returns 0."""
        target = _mock_target(resource_count=0)
        self.assertEqual(get_current_count(target, "resources", 1), 0)

    def test_mob_uses_resources_dict(self):
        """Mobs/containers use db.resources dict."""
        target = _mock_target(resources={8: 3, 1: 5})
        self.assertEqual(get_current_count(target, "resources", 8), 3)
        self.assertEqual(get_current_count(target, "resources", 1), 5)

    def test_mob_missing_key_returns_zero(self):
        """Missing resource key returns 0."""
        target = _mock_target(resources={8: 3})
        self.assertEqual(get_current_count(target, "resources", 1), 0)

    def test_mob_no_resources_attr(self):
        """Target with no resources attribute returns 0."""
        target = _mock_target()
        target.db.resources = None
        self.assertEqual(get_current_count(target, "resources", 1), 0)

    def test_string_key_fallback(self):
        """Handles Evennia's string key serialization."""
        target = _mock_target(resources={"8": 3})
        self.assertEqual(get_current_count(target, "resources", 8), 3)


class TestGetCurrentCountGold(EvenniaTest):

    def create_script(self):
        pass

    def test_gold_returns_db_gold(self):
        target = _mock_target(gold=42)
        self.assertEqual(get_current_count(target, "gold", "gold"), 42)

    def test_gold_none_returns_zero(self):
        target = _mock_target(gold=None)
        self.assertEqual(get_current_count(target, "gold", "gold"), 0)

    def test_gold_missing_attr_returns_zero(self):
        target = _mock_target()
        target.db.gold = None
        self.assertEqual(get_current_count(target, "gold", "gold"), 0)


class TestCountNfts(EvenniaTest):

    def create_script(self):
        pass

    def _make_nft(self, typeclass_path, prototype_key=None):
        """Create a mock NFT item."""
        item = MagicMock()
        item.typeclass_path = typeclass_path
        item.db = MagicMock()
        item.db.prototype_key = prototype_key
        return item

    def test_count_scrolls_in_contents(self):
        """Counts spell scrolls in target contents by typeclass."""
        target = _mock_target()
        target.db.wearslots = None
        scroll1 = self._make_nft("typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem")
        scroll2 = self._make_nft("typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem")
        weapon = self._make_nft("typeclasses.items.weapons.longsword_nft_item.LongswordNFTItem")
        target.contents = [scroll1, scroll2, weapon]
        self.assertEqual(count_nfts(target, "scrolls"), 2)

    def test_count_recipes_in_contents(self):
        """Counts recipe scrolls in target contents by typeclass."""
        target = _mock_target()
        target.db.wearslots = None
        recipe = self._make_nft("typeclasses.items.consumables.crafting_recipe_nft_item.CraftingRecipeNFTItem")
        scroll = self._make_nft("typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem")
        target.contents = [recipe, scroll]
        self.assertEqual(count_nfts(target, "recipes"), 1)

    def test_count_nfts_exact_match(self):
        """Counts rare NFTs by exact prototype_key match."""
        target = _mock_target()
        target.db.wearslots = None
        lightning = self._make_nft("typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem", "jupiters_lightning")
        other = self._make_nft("typeclasses.items.weapons.weapon_nft_item.WeaponNFTItem", "iron_sword")
        target.contents = [lightning, other]
        self.assertEqual(count_nfts(target, "nfts", "jupiters_lightning"), 1)

    def test_count_includes_equipped(self):
        """Items in wearslots are counted too."""
        target = _mock_target()
        equipped_scroll = self._make_nft("typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem")
        target.db.wearslots = {"held_right": equipped_scroll}
        target.contents = []  # Not in contents, only equipped
        self.assertEqual(count_nfts(target, "scrolls"), 1)

    def test_no_double_counting(self):
        """Items in both contents and wearslots counted once."""
        target = _mock_target()
        scroll = self._make_nft("typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem")
        target.db.wearslots = {"held_right": scroll}
        target.contents = [scroll]  # Same item in both
        self.assertEqual(count_nfts(target, "scrolls"), 1)

    def test_empty_target(self):
        """Empty target returns 0."""
        target = _mock_target()
        target.db.wearslots = None
        target.contents = []
        self.assertEqual(count_nfts(target, "scrolls"), 0)
        self.assertEqual(count_nfts(target, "nfts", "something"), 0)
