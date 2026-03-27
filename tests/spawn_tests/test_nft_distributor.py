"""Tests for NFT distributors — tier filtering and placement."""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.distributors.nft import (
    ScrollDistributor,
    RecipeDistributor,
    RareNFTDistributor,
    TIER_ORDER,
    TIER_RANK,
)

_TEST_CONFIG = {
    ("knowledge", "scroll_magic_missile"): {
        "calculator": "knowledge",
        "base_drop_rate": 2,
        "tier": "basic",
    },
    ("knowledge", "scroll_fireball"): {
        "calculator": "knowledge",
        "base_drop_rate": 1,
        "tier": "skilled",
    },
    ("knowledge", "scroll_vampiric_touch"): {
        "calculator": "knowledge",
        "base_drop_rate": 1,
        "tier": "gm",
    },
}


def _mock_target_with_scrolls_max(max_dict, current_scrolls=0):
    """Create a mock mob target with spawn_scrolls_max."""
    target = MagicMock()
    target.db = MagicMock()
    target.db.spawn_scrolls_max = max_dict
    target.db.wearslots = None
    # Mock contents to simulate current scroll count
    target.contents = [
        _make_scroll() for _ in range(current_scrolls)
    ]
    return target


def _make_scroll():
    """Create a mock spell scroll item."""
    item = MagicMock()
    item.typeclass_path = "typeclasses.items.consumables.spell_scroll_nft_item.SpellScrollNFTItem"
    item.db = MagicMock()
    item.db.prototype_key = None
    return item


class TestTierConstants(EvenniaTest):

    def create_script(self):
        pass

    def test_tier_order(self):
        self.assertEqual(TIER_ORDER, ["basic", "skilled", "expert", "master", "gm"])

    def test_tier_rank(self):
        self.assertEqual(TIER_RANK["basic"], 0)
        self.assertEqual(TIER_RANK["gm"], 4)
        self.assertTrue(TIER_RANK["basic"] < TIER_RANK["skilled"])
        self.assertTrue(TIER_RANK["skilled"] < TIER_RANK["expert"])


class TestScrollDistributorTierFiltering(EvenniaTest):

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", _TEST_CONFIG)
    def test_basic_scroll_fits_in_basic_slot(self):
        """Basic scroll fits in basic:1 slot."""
        dist = ScrollDistributor()
        target = _mock_target_with_scrolls_max(
            {"basic": 1, "skilled": 0, "expert": 0, "master": 0, "gm": 0},
        )
        result = dist._get_max_for_key(target, "scroll_magic_missile")
        self.assertEqual(result, 1)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", _TEST_CONFIG)
    def test_basic_scroll_fits_in_gm_slot(self):
        """Basic scroll fits in gm:1 slot (at-or-below)."""
        dist = ScrollDistributor()
        target = _mock_target_with_scrolls_max(
            {"basic": 0, "skilled": 0, "expert": 0, "master": 0, "gm": 1},
        )
        result = dist._get_max_for_key(target, "scroll_magic_missile")
        self.assertEqual(result, 1)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", _TEST_CONFIG)
    def test_skilled_scroll_does_not_fit_basic_slot(self):
        """Skilled scroll does NOT fit in basic:1 slot only."""
        dist = ScrollDistributor()
        target = _mock_target_with_scrolls_max(
            {"basic": 1, "skilled": 0, "expert": 0, "master": 0, "gm": 0},
        )
        result = dist._get_max_for_key(target, "scroll_fireball")
        self.assertEqual(result, 0)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", _TEST_CONFIG)
    def test_gm_scroll_only_fits_gm_slot(self):
        """GM scroll only fits in gm slot."""
        dist = ScrollDistributor()
        target = _mock_target_with_scrolls_max(
            {"basic": 1, "skilled": 1, "expert": 1, "master": 1, "gm": 1},
        )
        result = dist._get_max_for_key(target, "scroll_vampiric_touch")
        # Only gm slot accepts gm scrolls → 1
        self.assertEqual(result, 1)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", _TEST_CONFIG)
    def test_multiple_slots_summed(self):
        """Multiple compatible slots are summed."""
        dist = ScrollDistributor()
        target = _mock_target_with_scrolls_max(
            {"basic": 2, "skilled": 1, "expert": 0, "master": 0, "gm": 1},
        )
        result = dist._get_max_for_key(target, "scroll_magic_missile")
        # basic can use: basic(2) + skilled(1) + gm(1) = 4
        self.assertEqual(result, 4)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", _TEST_CONFIG)
    def test_existing_scrolls_reduce_headroom(self):
        """Current scrolls reduce available slots."""
        dist = ScrollDistributor()
        target = _mock_target_with_scrolls_max(
            {"basic": 2, "skilled": 0, "expert": 0, "master": 0, "gm": 0},
            current_scrolls=1,
        )
        result = dist._get_max_for_key(target, "scroll_magic_missile")
        # 2 slots - 1 existing = 1
        self.assertEqual(result, 1)

    @patch("blockchain.xrpl.services.spawn.config.SPAWN_CONFIG", _TEST_CONFIG)
    def test_all_slots_full(self):
        """All slots full → 0 headroom."""
        dist = ScrollDistributor()
        target = _mock_target_with_scrolls_max(
            {"basic": 1, "skilled": 0, "expert": 0, "master": 0, "gm": 0},
            current_scrolls=1,
        )
        result = dist._get_max_for_key(target, "scroll_magic_missile")
        self.assertEqual(result, 0)


class TestRareNFTDistributorExactMatch(EvenniaTest):

    def create_script(self):
        pass

    def test_exact_match_has_headroom(self):
        """Target with specific item key has headroom."""
        dist = RareNFTDistributor()
        target = MagicMock()
        target.db = MagicMock()
        target.db.spawn_nfts_max = {"UniqueWeapon.jupiters_lightning": 1}
        result = dist._get_max_for_key(target, "UniqueWeapon.jupiters_lightning")
        self.assertEqual(result, 1)

    def test_exact_match_wrong_key(self):
        """Target without specific item key has no headroom."""
        dist = RareNFTDistributor()
        target = MagicMock()
        target.db = MagicMock()
        target.db.spawn_nfts_max = {"UniqueWeapon.jupiters_lightning": 1}
        result = dist._get_max_for_key(target, "UniqueWeapon.iron_sword")
        self.assertEqual(result, 0)

    def test_no_max_attr(self):
        """Target without spawn_nfts_max attribute has no headroom."""
        dist = RareNFTDistributor()
        target = MagicMock()
        target.db = MagicMock()
        target.db.spawn_nfts_max = None
        result = dist._get_max_for_key(target, "UniqueWeapon.jupiters_lightning")
        self.assertEqual(result, 0)
