"""Tests for spawn/reader.py — the values-only capacity and count queries.

Every test here uses real Evennia objects with real attributes and real
contents. The reader exists to answer questions without materialising
typeclass instances, so mocking the objects would test nothing.

A note on perspective, because two different things are easily confused:

  - "inventory" (game concept) is the subset of an object's contents NOT
    flagged as worn.
  - "contents" (programmatic) is everything the object holds — inventory
    plus everything worn.

The reader uses the CONTENTS perspective throughout: an equipped weapon
still occupies its spawn slot, so capacity counting must include worn
items. Each test below states which perspective it exercises where the
distinction could matter.

evennia test --settings settings tests.spawn_tests.test_reader
"""

from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.reader import (
    TIER_ORDER,
    TIER_RANK,
    query_targets,
    read_capacity,
    read_current,
)

# Knowledge entries carry a tier, which decides which slots an item may
# occupy. Patched in for the tier tests so they do not depend on whatever
# populate_knowledge_config() happens to have generated.
_TEST_CONFIG = {
    ("knowledge", "scroll_basic"): {"calculator": "knowledge", "tier": "basic"},
    ("knowledge", "scroll_skilled"): {"calculator": "knowledge", "tier": "skilled"},
    ("knowledge", "scroll_gm"): {"calculator": "knowledge", "tier": "gm"},
}
_PATCH_CONFIG = "blockchain.xrpl.services.spawn.config.SPAWN_CONFIG"

SCROLL_TYPECLASS = (
    "typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem"
)
RECIPE_TYPECLASS = (
    "typeclasses.items.consumables.crafting_recipe_nft_item.CraftingRecipeNFTItem"
)


def _make_target(key="Target", tags=(), **attrs):
    """Create a real object with the given spawn tags and attributes."""
    obj = create.create_object(
        "evennia.objects.objects.DefaultObject", key=key, nohome=True,
    )
    for tag in tags:
        obj.tags.add(tag, category=tag)
    for name, value in attrs.items():
        obj.attributes.add(name, value)
    return obj


def _put_in(container, typeclass, key="item", **attrs):
    """Create an object inside container's contents."""
    obj = create.create_object(typeclass, key=key, nohome=True)
    for name, value in attrs.items():
        obj.attributes.add(name, value)
    obj.location = container
    return obj


# ================================================================== #
#  query_targets
# ================================================================== #


class TestQueryTargets(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_returns_pks_of_tagged_objects(self):
        a = _make_target("A", tags=("spawn_resources",))
        b = _make_target("B", tags=("spawn_resources",))
        result = query_targets("spawn_resources")
        self.assertIn(a.pk, result)
        self.assertIn(b.pk, result)

    def test_excludes_untagged_objects(self):
        tagged = _make_target("Tagged", tags=("spawn_gold",))
        untagged = _make_target("Untagged")
        result = query_targets("spawn_gold")
        self.assertIn(tagged.pk, result)
        self.assertNotIn(untagged.pk, result)

    def test_other_tag_not_returned(self):
        _make_target("Gold", tags=("spawn_gold",))
        self.assertEqual(query_targets("spawn_scrolls"), {})

    def test_no_matches_returns_empty(self):
        self.assertEqual(query_targets("spawn_nothing"), {})

    def test_maps_pk_to_owning_shard(self):
        """The owning shard comes back from the same query that finds the
        targets — no second lookup to attribute ownership.

        Mode-aware because both modes are genuinely run: under `settings`
        there is no shard_id column so every pk maps to None, and under
        `settings_shard0` the real owner is projected.
        """
        from evennia_shards import ROLE_MONOLITH, get_role, get_shard_id

        a = _make_target("A", tags=("spawn_resources",))
        result = query_targets("spawn_resources")
        self.assertIn(a.pk, result)
        if get_role() == ROLE_MONOLITH:
            self.assertIsNone(result[a.pk])
        else:
            self.assertEqual(result[a.pk], get_shard_id())


# ================================================================== #
#  read_capacity — resources
# ================================================================== #


class TestReadCapacityResources(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_int_key(self):
        t = _make_target(spawn_resources_max={8: 3})
        self.assertEqual(read_capacity([t.pk], "resources", 8), {t.pk: 3})

    def test_string_key_fallback(self):
        """Attributes authored with string keys must still resolve."""
        t = _make_target(spawn_resources_max={"8": 5})
        self.assertEqual(read_capacity([t.pk], "resources", 8), {t.pk: 5})

    def test_key_absent_from_dict_is_zero(self):
        t = _make_target(spawn_resources_max={1: 10})
        self.assertEqual(read_capacity([t.pk], "resources", 8), {t.pk: 0})

    def test_missing_attribute_is_zero(self):
        t = _make_target()
        self.assertEqual(read_capacity([t.pk], "resources", 8), {t.pk: 0})

    def test_multiple_targets(self):
        a = _make_target("A", spawn_resources_max={1: 4})
        b = _make_target("B", spawn_resources_max={1: 7})
        result = read_capacity([a.pk, b.pk], "resources", 1)
        self.assertEqual(result, {a.pk: 4, b.pk: 7})


# ================================================================== #
#  read_capacity — gold
# ================================================================== #


class TestReadCapacityGold(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_plain_int(self):
        """Gold is the one category storing a bare int, not a dict."""
        t = _make_target(spawn_gold_max=12)
        self.assertEqual(read_capacity([t.pk], "gold", "gold"), {t.pk: 12})

    def test_missing_attribute_is_zero(self):
        t = _make_target()
        self.assertEqual(read_capacity([t.pk], "gold", "gold"), {t.pk: 0})


# ================================================================== #
#  read_capacity — scrolls and recipes (at-or-below tiers)
# ================================================================== #


class TestReadCapacityTiered(EvenniaTest):
    """A slot accepts its own tier or any lower one, so capacity for an item
    is the sum of slots at its tier and above."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_basic_item_fits_basic_slot(self):
        t = _make_target(spawn_scrolls_max={"basic": 1})
        result = read_capacity([t.pk], "scrolls", "scroll_unknown_basic")
        self.assertEqual(result, {t.pk: 1})

    def test_basic_item_also_counts_higher_slots(self):
        """basic <= expert <= gm, so all three slots accept a basic scroll."""
        t = _make_target(spawn_scrolls_max={"basic": 1, "expert": 1, "gm": 2})
        result = read_capacity([t.pk], "scrolls", "scroll_unknown_basic")
        self.assertEqual(result, {t.pk: 4})

    def test_zero_slots_ignored(self):
        t = _make_target(
            spawn_scrolls_max={"basic": 1, "skilled": 0, "expert": 0, "gm": 0},
        )
        result = read_capacity([t.pk], "scrolls", "scroll_unknown_basic")
        self.assertEqual(result, {t.pk: 1})

    def test_recipes_use_the_same_rule(self):
        t = _make_target(spawn_recipes_max={"basic": 2, "gm": 1})
        result = read_capacity([t.pk], "recipes", "recipe_unknown_basic")
        self.assertEqual(result, {t.pk: 3})

    def test_missing_attribute_is_zero(self):
        t = _make_target()
        result = read_capacity([t.pk], "scrolls", "scroll_unknown_basic")
        self.assertEqual(result, {t.pk: 0})

    @patch(_PATCH_CONFIG, _TEST_CONFIG)
    def test_higher_tier_item_does_not_fit_lower_slot(self):
        """A skilled scroll cannot go in a basic-only slot."""
        t = _make_target(spawn_scrolls_max={"basic": 1})
        result = read_capacity([t.pk], "scrolls", "scroll_skilled")
        self.assertEqual(result, {t.pk: 0})

    @patch(_PATCH_CONFIG, _TEST_CONFIG)
    def test_gm_item_fits_only_gm_slot(self):
        """The most restrictive case — gm items fit nowhere else."""
        t = _make_target(
            spawn_scrolls_max={"basic": 2, "skilled": 2, "expert": 2, "gm": 1},
        )
        result = read_capacity([t.pk], "scrolls", "scroll_gm")
        self.assertEqual(result, {t.pk: 1})

    @patch(_PATCH_CONFIG, _TEST_CONFIG)
    def test_basic_item_fits_every_slot(self):
        """The most permissive case — the mirror of the gm test above."""
        t = _make_target(
            spawn_scrolls_max={"basic": 2, "skilled": 2, "expert": 2, "gm": 1},
        )
        result = read_capacity([t.pk], "scrolls", "scroll_basic")
        self.assertEqual(result, {t.pk: 7})


class TestTierConstants(EvenniaTest):
    """The tier hierarchy the at-or-below rule depends on."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_tier_order(self):
        self.assertEqual(
            TIER_ORDER, ["basic", "skilled", "expert", "master", "gm"],
        )

    def test_tier_rank_ascends(self):
        self.assertEqual(TIER_RANK["basic"], 0)
        self.assertEqual(TIER_RANK["gm"], 4)
        self.assertLess(TIER_RANK["basic"], TIER_RANK["skilled"])
        self.assertLess(TIER_RANK["skilled"], TIER_RANK["expert"])
        self.assertLess(TIER_RANK["expert"], TIER_RANK["master"])


# ================================================================== #
#  read_capacity — rare NFTs (exact match)
# ================================================================== #


class TestReadCapacityRareNFT(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_exact_match(self):
        t = _make_target(spawn_nfts_max={"UniqueWeapon.jupiters_lightning": 1})
        result = read_capacity(
            [t.pk], "nfts", "UniqueWeapon.jupiters_lightning",
        )
        self.assertEqual(result, {t.pk: 1})

    def test_no_at_or_below_for_rare(self):
        """Rare NFT keys are item identities, not tiers — no fallback."""
        t = _make_target(spawn_nfts_max={"UniqueWeapon.jupiters_lightning": 1})
        result = read_capacity([t.pk], "nfts", "UniqueWeapon.iron_sword")
        self.assertEqual(result, {t.pk: 0})

    def test_no_max_attribute_is_zero(self):
        """A target with no spawn_nfts_max holds no rare items at all."""
        t = _make_target()
        result = read_capacity(
            [t.pk], "nfts", "UniqueWeapon.jupiters_lightning",
        )
        self.assertEqual(result, {t.pk: 0})


# ================================================================== #
#  read_current — resources
# ================================================================== #


class TestReadCurrentResources(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_harvest_room_uses_resource_count(self):
        """Harvest rooms embed resources in the environment and track a
        single int, rather than using the FungibleInventoryMixin dict."""
        t = _make_target(resource_count=7)
        self.assertEqual(read_current([t.pk], "resources", 1), {t.pk: 7})

    def test_mob_uses_resources_dict(self):
        t = _make_target(resources={8: 2})
        self.assertEqual(read_current([t.pk], "resources", 8), {t.pk: 2})

    def test_resources_dict_string_key_fallback(self):
        t = _make_target(resources={"8": 4})
        self.assertEqual(read_current([t.pk], "resources", 8), {t.pk: 4})

    def test_resource_count_none_falls_through_to_dict(self):
        """The object path discriminates on `is not None`, and an absent
        attribute row reads as None in values terms. A target with
        resource_count explicitly None must use the resources dict."""
        t = _make_target(resource_count=None, resources={8: 6})
        self.assertEqual(read_current([t.pk], "resources", 8), {t.pk: 6})

    def test_resource_count_zero_is_not_treated_as_missing(self):
        """An empty harvest room holds 0, and must not fall through."""
        t = _make_target(resource_count=0, resources={8: 99})
        self.assertEqual(read_current([t.pk], "resources", 8), {t.pk: 0})

    def test_neither_attribute_is_zero(self):
        t = _make_target()
        self.assertEqual(read_current([t.pk], "resources", 8), {t.pk: 0})


# ================================================================== #
#  read_current — gold
# ================================================================== #


class TestReadCurrentGold(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_gold_attribute(self):
        t = _make_target(gold=15)
        self.assertEqual(read_current([t.pk], "gold", "gold"), {t.pk: 15})

    def test_explicit_zero(self):
        t = _make_target(gold=0)
        self.assertEqual(read_current([t.pk], "gold", "gold"), {t.pk: 0})

    def test_explicit_none(self):
        """A gold attribute set to None reads as empty, not as an error."""
        t = _make_target(gold=None)
        self.assertEqual(read_current([t.pk], "gold", "gold"), {t.pk: 0})

    def test_missing_is_zero(self):
        t = _make_target()
        self.assertEqual(read_current([t.pk], "gold", "gold"), {t.pk: 0})


# ================================================================== #
#  read_current — NFTs, counted from contents
# ================================================================== #


class TestReadCurrentNFTs(EvenniaTest):
    """CONTENTS perspective: everything the target holds counts toward
    capacity, whether or not it is flagged as worn."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_counts_scrolls_in_contents(self):
        t = _make_target()
        _put_in(t, SCROLL_TYPECLASS, "s1")
        _put_in(t, SCROLL_TYPECLASS, "s2")
        result = read_current([t.pk], "scrolls", "scroll_magic_missile")
        self.assertEqual(result, {t.pk: 2})

    def test_recipes_counted_separately_from_scrolls(self):
        t = _make_target()
        _put_in(t, SCROLL_TYPECLASS, "s1")
        _put_in(t, RECIPE_TYPECLASS, "r1")
        self.assertEqual(
            read_current([t.pk], "recipes", "recipe_bread"), {t.pk: 1},
        )
        self.assertEqual(
            read_current([t.pk], "scrolls", "scroll_magic_missile"), {t.pk: 1},
        )

    def test_worn_item_still_counts(self):
        """CONTENTS perspective. Wearing does not move an item — it stays in
        contents and only a db.wearslots reference is added. An equipped
        item still occupies its spawn slot, so it must count, and must
        count exactly once."""
        t = _make_target()
        scroll = _put_in(t, SCROLL_TYPECLASS, "worn")
        t.attributes.add("wearslots", {"held_right": scroll})
        result = read_current([t.pk], "scrolls", "scroll_magic_missile")
        self.assertEqual(result, {t.pk: 1})

    def test_items_elsewhere_not_counted(self):
        t = _make_target("Target")
        other = _make_target("Other")
        _put_in(other, SCROLL_TYPECLASS, "s1")
        result = read_current([t.pk], "scrolls", "scroll_magic_missile")
        self.assertEqual(result, {t.pk: 0})

    def test_rare_nft_matched_by_prototype_key(self):
        t = _make_target()
        _put_in(t, SCROLL_TYPECLASS, "match", prototype_key="jupiters_lightning")
        _put_in(t, SCROLL_TYPECLASS, "other", prototype_key="iron_sword")
        result = read_current([t.pk], "nfts", "jupiters_lightning")
        self.assertEqual(result, {t.pk: 1})

    def test_empty_target_is_zero(self):
        t = _make_target()
        result = read_current([t.pk], "scrolls", "scroll_magic_missile")
        self.assertEqual(result, {t.pk: 0})


# ================================================================== #
#  The category filter — load-bearing, mutation-tested
# ================================================================== #


class TestAttributeCategoryFilter(EvenniaTest):
    """`target.db.x` reads the attribute with category=None. Without the
    isnull filter on the join, a same-named attribute in another category
    joins as an extra row and silently corrupts the reading."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_capacity_ignores_other_categories(self):
        t = _make_target(spawn_gold_max=12)
        t.attributes.add("spawn_gold_max", 999, category="decoy")
        self.assertEqual(read_capacity([t.pk], "gold", "gold"), {t.pk: 12})

    def test_current_ignores_other_categories(self):
        t = _make_target(gold=15)
        t.attributes.add("gold", 999, category="decoy")
        self.assertEqual(read_current([t.pk], "gold", "gold"), {t.pk: 15})

    def test_rare_nft_prototype_ignores_other_categories(self):
        t = _make_target()
        item = _put_in(t, SCROLL_TYPECLASS, "item", prototype_key="iron_sword")
        item.attributes.add(
            "prototype_key", "jupiters_lightning", category="decoy",
        )
        result = read_current([t.pk], "nfts", "jupiters_lightning")
        self.assertEqual(result, {t.pk: 0})


# ================================================================== #
#  Empty input
# ================================================================== #


class TestEmptyInput(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_capacity_empty_pks(self):
        self.assertEqual(read_capacity([], "resources", 1), {})

    def test_current_empty_pks(self):
        self.assertEqual(read_current([], "resources", 1), {})

    def test_current_nfts_empty_pks(self):
        self.assertEqual(read_current([], "scrolls", "scroll_x"), {})

    def test_unknown_category_is_zero(self):
        t = _make_target()
        self.assertEqual(read_capacity([t.pk], "bogus", "x"), {t.pk: 0})
        self.assertEqual(read_current([t.pk], "bogus", "x"), {t.pk: 0})
