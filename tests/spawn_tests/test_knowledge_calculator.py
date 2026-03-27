"""Tests for KnowledgeCalculator."""

from unittest.mock import patch, MagicMock

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.calculators.knowledge import KnowledgeCalculator

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
}


class TestKnowledgeCalculator(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=0.0)
    def test_zero_saturation_full_budget(self, mock_sat):
        """0% saturation → full base_drop_rate."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_magic_missile")
        self.assertEqual(result, 2)

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=0.5)
    def test_half_saturation(self, mock_sat):
        """50% saturation → half budget."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_magic_missile")
        # 2 * (1.0 - 0.5) = 1.0 → 1
        self.assertEqual(result, 1)

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=1.0)
    def test_full_saturation_zero_budget(self, mock_sat):
        """100% saturation → zero budget."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_magic_missile")
        self.assertEqual(result, 0)

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=1.5)
    def test_over_saturation_clamped_to_zero(self, mock_sat):
        """Saturation > 1.0 → still zero budget (max(0, ...))."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_magic_missile")
        self.assertEqual(result, 0)

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=None)
    def test_no_eligible_players_zero_budget(self, mock_sat):
        """No eligible players (saturation=None) → zero budget."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_magic_missile")
        self.assertEqual(result, 0)

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=None)
    def test_no_snapshot_zero_budget(self, mock_sat):
        """No snapshot data → zero budget."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_fireball")
        self.assertEqual(result, 0)

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=0.1)
    def test_low_saturation_near_full_budget(self, mock_sat):
        """10% saturation → 90% of base rate."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_magic_missile")
        # 2 * 0.9 = 1.8 → 2
        self.assertEqual(result, 2)

    @patch.object(KnowledgeCalculator, "_get_saturation", return_value=0.8)
    def test_high_saturation_low_budget(self, mock_sat):
        """80% saturation → 20% of base rate, rounds to 0 for rate=1."""
        calc = KnowledgeCalculator(_TEST_CONFIG)
        result = calc.calculate("knowledge", "scroll_fireball")
        # 1 * 0.2 = 0.2 → 0
        self.assertEqual(result, 0)
