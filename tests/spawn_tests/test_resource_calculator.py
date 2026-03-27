"""Tests for ResourceCalculator."""

from decimal import Decimal
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.calculators.resource import ResourceCalculator

_TEST_CONFIG = {
    ("resource", 1): {
        "calculator": "resource",
        "default_spawn_rate": 10,
        "target_price_low": 8,
        "target_price_high": 16,
        "modifier_min": 0.25,
        "modifier_max": 2.0,
    },
}


class TestResourceCalculatorPriceModifier(EvenniaTest):

    def create_script(self):
        pass

    def setUp(self):
        super().setUp()
        self.calc = ResourceCalculator(_TEST_CONFIG)
        self.cfg = _TEST_CONFIG[("resource", 1)]

    def test_no_amm_returns_neutral(self):
        """No AMM pool (None price) → 1.0."""
        self.assertEqual(self.calc.price_modifier(None, self.cfg), 1.0)

    def test_price_at_midpoint_returns_one(self):
        """Price at exact midpoint → 1.0."""
        result = self.calc.price_modifier(Decimal("12"), self.cfg)
        self.assertAlmostEqual(result, 1.0, places=5)

    def test_price_at_low_returns_min(self):
        """Price at low band → modifier_min."""
        result = self.calc.price_modifier(Decimal("8"), self.cfg)
        self.assertAlmostEqual(result, 0.25, places=5)

    def test_price_below_low_returns_min(self):
        """Price below low band → clamped to modifier_min."""
        result = self.calc.price_modifier(Decimal("1"), self.cfg)
        self.assertAlmostEqual(result, 0.25, places=5)

    def test_price_at_high_returns_max(self):
        """Price at high band → modifier_max."""
        result = self.calc.price_modifier(Decimal("16"), self.cfg)
        self.assertAlmostEqual(result, 2.0, places=5)

    def test_price_above_high_returns_max(self):
        """Price above high band → clamped to modifier_max."""
        result = self.calc.price_modifier(Decimal("100"), self.cfg)
        self.assertAlmostEqual(result, 2.0, places=5)

    def test_price_between_low_and_mid(self):
        """Price between low and midpoint → between min and 1.0."""
        result = self.calc.price_modifier(Decimal("10"), self.cfg)
        # low=8, mid=12, t=(10-8)/(12-8)=0.5
        # expected = 0.25 + 0.5 * (1.0 - 0.25) = 0.625
        self.assertAlmostEqual(result, 0.625, places=5)

    def test_price_between_mid_and_high(self):
        """Price between midpoint and high → between 1.0 and max."""
        result = self.calc.price_modifier(Decimal("14"), self.cfg)
        # mid=12, high=16, t=(14-12)/(16-12)=0.5
        # expected = 1.0 + 0.5 * (2.0 - 1.0) = 1.5
        self.assertAlmostEqual(result, 1.5, places=5)


class TestResourceCalculatorCalculate(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    @patch.object(ResourceCalculator, "_get_latest_buy_price", return_value=None)
    @patch.object(ResourceCalculator, "_get_avg_consumption", return_value=Decimal(0))
    def test_cold_start_uses_default(self, mock_cons, mock_price):
        """No consumption data → uses default_spawn_rate."""
        calc = ResourceCalculator(_TEST_CONFIG)
        result = calc.calculate("resource", 1)
        # default=10, price_mod=1.0 (no AMM) → 10
        self.assertEqual(result, 10)

    @patch.object(ResourceCalculator, "_get_latest_buy_price", return_value=Decimal("12"))
    @patch.object(ResourceCalculator, "_get_avg_consumption", return_value=Decimal("20"))
    def test_consumption_with_neutral_price(self, mock_cons, mock_price):
        """Consumption × neutral price (midpoint) → consumption."""
        calc = ResourceCalculator(_TEST_CONFIG)
        result = calc.calculate("resource", 1)
        # consumption=20, price at midpoint(12) → mod=1.0, budget=20
        self.assertEqual(result, 20)

    @patch.object(ResourceCalculator, "_get_latest_buy_price", return_value=Decimal("16"))
    @patch.object(ResourceCalculator, "_get_avg_consumption", return_value=Decimal("10"))
    def test_high_price_boosts_spawn(self, mock_cons, mock_price):
        """High price → modifier_max → doubled budget."""
        calc = ResourceCalculator(_TEST_CONFIG)
        result = calc.calculate("resource", 1)
        # consumption=10, price=16(high) → mod=2.0, budget=20
        self.assertEqual(result, 20)

    @patch.object(ResourceCalculator, "_get_latest_buy_price", return_value=Decimal("8"))
    @patch.object(ResourceCalculator, "_get_avg_consumption", return_value=Decimal("10"))
    def test_low_price_reduces_spawn(self, mock_cons, mock_price):
        """Low price → modifier_min → reduced budget."""
        calc = ResourceCalculator(_TEST_CONFIG)
        result = calc.calculate("resource", 1)
        # consumption=10, price=8(low) → mod=0.25, budget=2.5→2 (banker's rounding)
        self.assertEqual(result, 2)
