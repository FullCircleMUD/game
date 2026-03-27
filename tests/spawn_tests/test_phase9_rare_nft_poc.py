"""Tests for Phase 9 — Unique NFT Spawning POC.

Proves the architecture works end-to-end for rare items:
  - RareNFTCalculator returns fixed spawn rate from config
  - RareNFTDistributor uses exact-match on spawn_nfts_max
  - SpawnService routes rare_nft entries correctly
  - spawn_nfts tag + spawn_nfts_max on targets

evennia test --settings settings tests.spawn_tests.test_phase9_rare_nft_poc
"""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.calculators.rare_nft import RareNFTCalculator
from blockchain.xrpl.services.spawn.distributors.nft import RareNFTDistributor


_POC_CONFIG = {
    ("rare_nft", "TestUniqueWeapon.lightning_bolt"): {
        "calculator": "rare_nft",
        "spawn_rate": 1,
    },
}


# ================================================================== #
#  RareNFTCalculator
# ================================================================== #


class TestRareNFTCalculator(EvenniaTest):

    def create_script(self):
        pass

    def test_returns_spawn_rate(self):
        """Calculator returns the configured spawn_rate."""
        calc = RareNFTCalculator(_POC_CONFIG)
        result = calc.calculate("rare_nft", "TestUniqueWeapon.lightning_bolt")
        self.assertEqual(result, 1)

    def test_default_spawn_rate_is_one(self):
        """Missing spawn_rate defaults to 1."""
        config = {("rare_nft", "test"): {"calculator": "rare_nft"}}
        calc = RareNFTCalculator(config)
        result = calc.calculate("rare_nft", "test")
        self.assertEqual(result, 1)

    def test_zero_spawn_rate(self):
        """spawn_rate=0 returns 0."""
        config = {("rare_nft", "test"): {"calculator": "rare_nft", "spawn_rate": 0}}
        calc = RareNFTCalculator(config)
        result = calc.calculate("rare_nft", "test")
        self.assertEqual(result, 0)

    def test_override_spawn_rate(self):
        """Override spawn_rate via kwargs."""
        calc = RareNFTCalculator(_POC_CONFIG)
        result = calc.calculate(
            "rare_nft", "TestUniqueWeapon.lightning_bolt",
            spawn_rate=5,
        )
        self.assertEqual(result, 5)

    def test_missing_key_raises(self):
        """Unknown key raises KeyError."""
        calc = RareNFTCalculator(_POC_CONFIG)
        with self.assertRaises(KeyError):
            calc.calculate("rare_nft", "nonexistent")


# ================================================================== #
#  RareNFTDistributor — exact match
# ================================================================== #


class TestRareNFTDistributorExactMatchPOC(EvenniaTest):

    def create_script(self):
        pass

    def test_exact_match_headroom(self):
        """Target with matching key in spawn_nfts_max has headroom."""
        dist = RareNFTDistributor()
        target = MagicMock()
        target.db = MagicMock()
        target.db.spawn_nfts_max = {"TestUniqueWeapon.lightning_bolt": 1}
        result = dist._get_max_for_key(target, "TestUniqueWeapon.lightning_bolt")
        self.assertEqual(result, 1)

    def test_wrong_key_no_headroom(self):
        """Target without matching key has no headroom."""
        dist = RareNFTDistributor()
        target = MagicMock()
        target.db = MagicMock()
        target.db.spawn_nfts_max = {"TestUniqueWeapon.lightning_bolt": 1}
        result = dist._get_max_for_key(target, "TestUniqueWeapon.frost_blade")
        self.assertEqual(result, 0)

    def test_no_max_attr_no_headroom(self):
        """Target without spawn_nfts_max has no headroom."""
        dist = RareNFTDistributor()
        target = MagicMock()
        target.db = MagicMock()
        target.db.spawn_nfts_max = None
        result = dist._get_max_for_key(target, "TestUniqueWeapon.lightning_bolt")
        self.assertEqual(result, 0)

    def test_distributor_config(self):
        """RareNFTDistributor has correct tag and category."""
        dist = RareNFTDistributor()
        self.assertEqual(dist.tag_name, "spawn_nfts")
        self.assertEqual(dist.category, "nfts")
        self.assertEqual(dist.max_attr_name, "spawn_nfts_max")


# ================================================================== #
#  SpawnService routing — rare_nft
# ================================================================== #


class TestSpawnServiceRareNFTRouting(EvenniaTest):

    def create_script(self):
        pass

    def test_rare_nft_calculator_registered(self):
        """SpawnService maps 'rare_nft' to RareNFTCalculator."""
        from blockchain.xrpl.services.spawn.service import CALCULATOR_CLASSES
        self.assertIn("rare_nft", CALCULATOR_CLASSES)
        self.assertEqual(CALCULATOR_CLASSES["rare_nft"], RareNFTCalculator)

    def test_rare_nft_distributor_registered(self):
        """SpawnService maps 'rare_nft' to RareNFTDistributor."""
        from blockchain.xrpl.services.spawn.service import DISTRIBUTOR_MAP
        self.assertIn("rare_nft", DISTRIBUTOR_MAP)
        self.assertEqual(DISTRIBUTOR_MAP["rare_nft"], RareNFTDistributor)

    def test_get_distributor_routes_rare_nft(self):
        """_get_distributor returns RareNFTDistributor for rare_nft items."""
        from blockchain.xrpl.services.spawn.service import SpawnService
        svc = SpawnService(_POC_CONFIG)
        dist = svc._get_distributor("rare_nft", "TestUniqueWeapon.lightning_bolt")
        self.assertIsInstance(dist, RareNFTDistributor)


# ================================================================== #
#  End-to-end: calculator → budget → distributor routing
# ================================================================== #


class TestRareNFTPOCEndToEnd(EvenniaTest):
    """Verify the full pipeline: config → calculator → budget → distributor."""

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.spawn.config.populate_knowledge_config")
    def test_hourly_cycle_creates_budget(self, mock_populate):
        """run_hourly_cycle creates BudgetState for rare_nft entries."""
        from blockchain.xrpl.services.spawn.service import SpawnService

        svc = SpawnService(dict(_POC_CONFIG))
        svc.run_hourly_cycle()

        state_key = ("rare_nft", "TestUniqueWeapon.lightning_bolt")
        self.assertIn(state_key, svc.budget_states)
        bs = svc.budget_states[state_key]
        self.assertEqual(bs.total, 1)
        self.assertEqual(bs.remaining, 0)  # all scheduled via delay()

    def test_apply_tick_places_items(self):
        """_apply_tick on RareNFTDistributor places items on targets."""
        target = MagicMock()
        target.db = MagicMock()
        target.db.spawn_nfts_max = {"TestUniqueWeapon.lightning_bolt": 1}
        target.db.wearslots = None
        target.contents = []

        dist = RareNFTDistributor()
        bs = BudgetState(
            item_type="rare_nft",
            type_key="TestUniqueWeapon.lightning_bolt",
        )
        bs.reset_for_hour(1)

        with patch.object(dist, "_query_targets", return_value=[target]):
            with patch.object(dist, "_place") as mock_place:
                dist._apply_tick(
                    "TestUniqueWeapon.lightning_bolt", 1, bs, True,
                )
                mock_place.assert_called_once_with(
                    target, "TestUniqueWeapon.lightning_bolt", 1,
                )

    def test_calculator_produces_correct_budget(self):
        """RareNFTCalculator returns spawn_rate=1 for POC config."""
        calc = RareNFTCalculator(_POC_CONFIG)
        budget = calc.calculate("rare_nft", "TestUniqueWeapon.lightning_bolt")
        self.assertEqual(budget, 1)

    def test_budget_state_quest_debt_works(self):
        """Quest debt mechanics work for rare_nft budget states."""
        bs = BudgetState(item_type="rare_nft", type_key="TestUniqueWeapon.lightning_bolt")
        bs.reset_for_hour(1)
        bs.add_quest_debt(1)
        # Tick of 1, debt of 1 → effective = 0
        effective = bs.effective_tick_budget(1)
        self.assertEqual(effective, 0)
        self.assertEqual(bs.quest_debt, 0)
