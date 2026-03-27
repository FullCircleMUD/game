"""Tests for GoldCalculator."""

from decimal import Decimal
from unittest.mock import patch

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.calculators.gold import GoldCalculator

_TEST_CONFIG = {
    ("gold", "gold"): {
        "calculator": "gold",
        "default_spawn_rate": 50,
        "buffer": 1.15,
        "min_runway_days": 7,
    },
}


class TestGoldCalculator(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    @patch.object(GoldCalculator, "_get_gold_reserve", return_value=Decimal("100000"))
    @patch.object(GoldCalculator, "_get_avg_gold_sinks", return_value=Decimal(0))
    def test_cold_start_uses_default(self, mock_sinks, mock_reserve):
        """No consumption data → uses default_spawn_rate."""
        calc = GoldCalculator(_TEST_CONFIG)
        result = calc.calculate("gold", "gold")
        # default=50, buffer=1.15, reserve healthy → 50 * 1.15 = 57.4999... → 57
        self.assertEqual(result, 57)

    @patch.object(GoldCalculator, "_get_gold_reserve", return_value=Decimal("100000"))
    @patch.object(GoldCalculator, "_get_avg_gold_sinks", return_value=Decimal("100"))
    def test_consumption_with_healthy_reserve(self, mock_sinks, mock_reserve):
        """Consumption × buffer with healthy reserve → full budget."""
        calc = GoldCalculator(_TEST_CONFIG)
        result = calc.calculate("gold", "gold")
        # consumption=100, buffer=1.15, throttle=1.0 → 115
        self.assertEqual(result, 115)

    @patch.object(GoldCalculator, "_get_gold_reserve", return_value=Decimal("0"))
    @patch.object(GoldCalculator, "_get_avg_gold_sinks", return_value=Decimal("100"))
    def test_empty_reserve_stops_spawning(self, mock_sinks, mock_reserve):
        """Zero reserve → throttle = 0 → no spawning."""
        calc = GoldCalculator(_TEST_CONFIG)
        result = calc.calculate("gold", "gold")
        self.assertEqual(result, 0)

    @patch.object(GoldCalculator, "_get_gold_reserve")
    @patch.object(GoldCalculator, "_get_avg_gold_sinks", return_value=Decimal("100"))
    def test_low_reserve_throttles(self, mock_sinks, mock_reserve):
        """Reserve with ~3.5 days runway → throttle ≈ 0.5."""
        # hourly_budget_estimate = 100 * 1.15 = 115
        # daily_burn = 115 * 24 = 2760
        # runway for 3.5 days → reserve = 2760 * 3.5 = 9660
        mock_reserve.return_value = Decimal("9660")
        calc = GoldCalculator(_TEST_CONFIG)
        result = calc.calculate("gold", "gold")
        # throttle ≈ 0.5, budget ≈ 57.5 → 58 (float precision slightly above 57.5)
        self.assertEqual(result, 58)

    @patch.object(GoldCalculator, "_get_gold_reserve", return_value=Decimal("100000"))
    @patch.object(GoldCalculator, "_get_avg_gold_sinks", return_value=Decimal("100"))
    def test_buffer_override(self, mock_sinks, mock_reserve):
        """Override buffer via kwargs."""
        calc = GoldCalculator(_TEST_CONFIG)
        result = calc.calculate("gold", "gold", buffer=2.0)
        # consumption=100, buffer=2.0, throttle=1.0 → 200
        self.assertEqual(result, 200)


class TestReserveThrottle(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    @patch.object(GoldCalculator, "_get_gold_reserve", return_value=Decimal("100000"))
    def test_healthy_runway(self, mock_reserve):
        """Runway >= min_runway → throttle = 1.0."""
        result = GoldCalculator._reserve_throttle(100, {"min_runway_days": 7})
        self.assertEqual(result, 1.0)

    @patch.object(GoldCalculator, "_get_gold_reserve", return_value=Decimal("0"))
    def test_zero_reserve(self, mock_reserve):
        """Zero reserve → throttle = 0."""
        result = GoldCalculator._reserve_throttle(100, {"min_runway_days": 7})
        self.assertEqual(result, 0.0)

    def test_zero_budget(self):
        """Zero hourly budget → throttle = 1.0 (can't divide by zero)."""
        result = GoldCalculator._reserve_throttle(0, {"min_runway_days": 7})
        self.assertEqual(result, 1.0)

    @patch.object(GoldCalculator, "_get_gold_reserve")
    def test_linear_ramp(self, mock_reserve):
        """Reserve at half min_runway → throttle ≈ 0.5."""
        # hourly=100, daily=2400, min_runway=7, half=3.5 days
        mock_reserve.return_value = Decimal(str(100 * 24 * 3.5))
        result = GoldCalculator._reserve_throttle(100, {"min_runway_days": 7})
        self.assertAlmostEqual(result, 0.5, places=2)
