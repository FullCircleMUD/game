"""
Tests for utils/weight_check.py — weight check helpers used by commands.

evennia test --settings settings tests.utils_tests.test_weight_check
"""

from unittest.mock import MagicMock

from django.conf import settings
from django.test import TestCase

from utils.weight_check import (
    check_can_carry, get_item_weight, get_gold_weight, get_resource_weight,
)


class TestCheckCanCarry(TestCase):
    """Test check_can_carry helper."""

    databases = "__all__"

    def test_no_mixin_always_ok(self):
        """Objects without can_carry should always pass."""
        carrier = MagicMock(spec=[])  # no can_carry
        ok, msg = check_can_carry(carrier, 999.0)
        self.assertTrue(ok)
        self.assertIsNone(msg)

    def test_within_capacity(self):
        """Should pass when can_carry returns True."""
        carrier = MagicMock()
        carrier.can_carry.return_value = True
        ok, msg = check_can_carry(carrier, 5.0)
        self.assertTrue(ok)
        self.assertIsNone(msg)

    def test_over_capacity(self):
        """Should fail when can_carry returns False."""
        carrier = MagicMock()
        carrier.can_carry.return_value = False
        carrier.get_remaining_capacity.return_value = 2.0
        ok, msg = check_can_carry(carrier, 5.0)
        self.assertFalse(ok)
        self.assertIn("can't carry", msg)
        self.assertIn("5.0", msg)
        self.assertIn("2.0", msg)


class TestGetItemWeight(TestCase):
    """Test get_item_weight helper."""

    def test_normal_weight(self):
        """Should return the item's weight attribute."""
        item = MagicMock()
        item.weight = 3.5
        self.assertAlmostEqual(get_item_weight(item), 3.5)

    def test_no_weight_attr(self):
        """Should return 0.0 if item has no weight attribute."""
        item = MagicMock(spec=[])  # no weight attr
        self.assertAlmostEqual(get_item_weight(item), 0.0)

    def test_none_weight(self):
        """Should return 0.0 if weight is None."""
        item = MagicMock()
        item.weight = None
        self.assertAlmostEqual(get_item_weight(item), 0.0)

    def test_zero_weight(self):
        """Should return 0.0 for zero weight."""
        item = MagicMock()
        item.weight = 0.0
        self.assertAlmostEqual(get_item_weight(item), 0.0)


class TestGetGoldWeight(TestCase):
    """Test get_gold_weight helper."""

    def test_gold_weight(self):
        """Should use GOLD_WEIGHT_PER_UNIT_KG from settings."""
        weight = get_gold_weight(100)
        expected = 100 * settings.GOLD_WEIGHT_PER_UNIT_KG
        self.assertAlmostEqual(weight, expected)

    def test_zero_gold(self):
        """Zero gold should have zero weight."""
        self.assertAlmostEqual(get_gold_weight(0), 0.0)


class TestGetResourceWeight(TestCase):
    """Test get_resource_weight helper."""

    databases = "__all__"

    def test_known_resource(self):
        """Known resource should use weight from cache."""
        # Iron Ore (id=4) = 1.5 kg per unit
        weight = get_resource_weight(4, 10)
        self.assertAlmostEqual(weight, 15.0)

    def test_unknown_resource(self):
        """Unknown resource should return 0."""
        weight = get_resource_weight(9999, 10)
        self.assertAlmostEqual(weight, 0.0)

    def test_zero_amount(self):
        """Zero amount should return 0."""
        weight = get_resource_weight(4, 0)
        self.assertAlmostEqual(weight, 0.0)
