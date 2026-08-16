"""
Tests for CmdSpawnReportItems — role guard, plus the grouping logic
(scrolls / recipes / other) over spawned NFTGameState rows.

get_role() is imported locally inside func() (not at module level), so
the role guard is patched at its source, evennia_shards.get_role.

NFTItemType/NFTGameState are pre-seeded by a data migration (item type
templates, plus 200 blank RESERVE-location NFTGameState rows) — the
seeded rows never carry item_type or SPAWNED location, so they never
match this command's query and tests don't need to isolate against them.

evennia test --settings settings tests.command_tests.test_cmd_spawn_report_items
"""

from unittest.mock import patch

from evennia.utils.test_resources import EvenniaCommandTest

from blockchain.xrpl.models import NFTGameState, NFTItemType
from commands.account_cmds.cmd_spawn_report_items import CmdSpawnReportItems

VAULT = "rVAULT_TEST_ADDRESS"

_counter = [90000]


def _next_uri_id():
    _counter[0] += 1
    return _counter[0]


def _item_type(name, typeclass, tracking_token=None):
    return NFTItemType.objects.create(
        name=name, typeclass=typeclass, prototype_key=None,
        default_metadata={}, tracking_token=tracking_token,
    )


def _spawned_nft(item_type, location=NFTGameState.LOCATION_SPAWNED):
    uri_id = _next_uri_id()
    return NFTGameState.objects.create(
        nftoken_id=f"TESTTOKEN{uri_id}", uri_id=uri_id, taxon=0,
        owner_in_game=VAULT, location=location,
        item_type=item_type, metadata={},
    )


# ══════════════════════════════════════════════════════════════════════════
#  Role guard
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role")
class TestSpawnReportItemsRoleGuard(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_shard_blocked(self, mock_role):
        mock_role.return_value = "shard"
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("can only be run OOC on the router", result)

    def test_router_allowed(self, mock_role):
        mock_role.return_value = "router"
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("No NFTs currently spawned", result)

    def test_monolith_allowed(self, mock_role):
        mock_role.return_value = "monolith"
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("No NFTs currently spawned", result)


# ══════════════════════════════════════════════════════════════════════════
#  Report grouping
# ══════════════════════════════════════════════════════════════════════════

@patch("evennia_shards.get_role", return_value="monolith")
class TestSpawnReportItemsGrouping(EvenniaCommandTest):
    databases = {"default", "xrpl"}

    def create_script(self):
        pass

    def test_no_spawned_nfts_shows_message(self, _mock_role):
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("No NFTs currently spawned", result)

    def test_scroll_typeclass_grouped_under_spell_scrolls(self, _mock_role):
        it = _item_type(
            "ZZZ Test Scroll",
            "typeclasses.items.scrolls.spell_scroll_nft_item.SpellScrollNFTItem",
        )
        _spawned_nft(it)
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("Spell Scrolls", result)
        self.assertIn("ZZZ Test Scroll: 1", result)

    def test_recipe_typeclass_grouped_under_crafting_recipes(self, _mock_role):
        it = _item_type(
            "ZZZ Test Recipe",
            "typeclasses.items.recipes.crafting_recipe_nft_item.CraftingRecipeNFTItem",
        )
        _spawned_nft(it)
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("Crafting Recipes", result)
        self.assertIn("ZZZ Test Recipe: 1", result)

    def test_other_typeclass_grouped_under_other(self, _mock_role):
        it = _item_type(
            "ZZZ Test Other", "typeclasses.items.rare_nft_item.RareNFTItem",
        )
        _spawned_nft(it)
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("Other NFTs", result)
        self.assertIn("ZZZ Test Other: 1", result)

    def test_counts_aggregate_by_name(self, _mock_role):
        it = _item_type(
            "ZZZ Test Scroll",
            "typeclasses.items.scrolls.spell_scroll_nft_item.SpellScrollNFTItem",
        )
        _spawned_nft(it)
        _spawned_nft(it)
        _spawned_nft(it)
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("ZZZ Test Scroll: 3", result)

    def test_non_spawned_location_excluded(self, _mock_role):
        it = _item_type(
            "ZZZ Test Scroll",
            "typeclasses.items.scrolls.spell_scroll_nft_item.SpellScrollNFTItem",
        )
        _spawned_nft(it, location=NFTGameState.LOCATION_RESERVE)
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("No NFTs currently spawned", result)

    def test_total_spawned_sums_all_categories(self, _mock_role):
        scroll = _item_type(
            "ZZZ Test Scroll",
            "typeclasses.items.scrolls.spell_scroll_nft_item.SpellScrollNFTItem",
        )
        recipe = _item_type(
            "ZZZ Test Recipe",
            "typeclasses.items.recipes.crafting_recipe_nft_item.CraftingRecipeNFTItem",
        )
        other = _item_type("ZZZ Test Other", "typeclasses.items.rare_nft_item.RareNFTItem")
        _spawned_nft(scroll)
        _spawned_nft(recipe)
        _spawned_nft(other)
        _spawned_nft(other)
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("Total spawned: 4", result)

    def test_only_categories_with_items_are_shown(self, _mock_role):
        it = _item_type(
            "ZZZ Test Scroll",
            "typeclasses.items.scrolls.spell_scroll_nft_item.SpellScrollNFTItem",
        )
        _spawned_nft(it)
        result = self.call(CmdSpawnReportItems(), "", caller=self.account)
        self.assertIn("Spell Scrolls", result)
        self.assertNotIn("Crafting Recipes", result)
        self.assertNotIn("Other NFTs", result)
