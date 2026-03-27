"""Tests for ResourceDistributor and GoldDistributor."""

from unittest.mock import patch, MagicMock, call

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.distributors.base import BaseDistributor
from blockchain.xrpl.services.spawn.distributors.fungible import (
    ResourceDistributor,
    GoldDistributor,
)


def _mock_target(resource_count=None, resources=None, gold=None, max_dict=None):
    """Create a mock target with spawn attributes."""
    target = MagicMock()
    db = MagicMock()
    if resource_count is not None:
        db.resource_count = resource_count
    else:
        del db.resource_count
    db.resources = resources or {}
    db.gold = gold or 0
    db.wearslots = None
    target.db = db
    target.contents = []
    return target


class TestResourceDistributorPlace(EvenniaTest):

    def create_script(self):
        pass

    def test_place_on_harvest_room(self):
        """Harvest rooms: increment resource_count directly."""
        dist = ResourceDistributor()
        target = _mock_target(resource_count=5)
        dist._place(target, 1, 3)
        self.assertEqual(target.db.resource_count, 8)

    def test_place_on_mob(self):
        """Mobs: call receive_resource_from_reserve()."""
        dist = ResourceDistributor()
        target = _mock_target(resources={8: 1})
        dist._place(target, 8, 2)
        target.receive_resource_from_reserve.assert_called_once_with(8, 2)


class TestGoldDistributorPlace(EvenniaTest):

    def create_script(self):
        pass

    def test_place_gold(self):
        """Gold: call receive_gold_from_reserve()."""
        dist = GoldDistributor()
        target = MagicMock()
        dist._place(target, "gold", 10)
        target.receive_gold_from_reserve.assert_called_once_with(10)


class TestProportionalAllocation(EvenniaTest):

    def create_script(self):
        pass

    def test_proportional_by_headroom(self):
        """Budget distributed proportionally by headroom."""
        dist = ResourceDistributor()
        # 3 targets with headroom 10, 5, 5 → total 20, budget 10
        t1 = MagicMock()
        t2 = MagicMock()
        t3 = MagicMock()
        eligible = [(t1, 10), (t2, 5), (t3, 5)]

        allocations = dist._allocate_proportional(eligible, 10, 20)

        alloc_dict = {t: a for t, a in allocations}
        # t1: floor(10*10/20)=5, t2: floor(10*5/20)=2, t3: floor(10*5/20)=2 → total=9
        # Remainder 1 goes to first in order (t1)
        self.assertEqual(alloc_dict[t1], 6)
        self.assertEqual(alloc_dict[t2], 2)
        self.assertEqual(alloc_dict[t3], 2)

    def test_minimum_one_allocation(self):
        """Small headroom targets get minimum 1."""
        dist = ResourceDistributor()
        t1 = MagicMock()
        t2 = MagicMock()
        # headroom 1 vs 100, budget=5
        eligible = [(t1, 1), (t2, 100)]
        allocations = dist._allocate_proportional(eligible, 5, 101)

        alloc_dict = {t: a for t, a in allocations}
        # t1: raw=5*1/101≈0.05 → min 1, t2: raw=5*100/101≈4.95 → floor 4
        self.assertEqual(alloc_dict[t1], 1)
        self.assertEqual(alloc_dict[t2], 4)

    def test_budget_caps_allocation(self):
        """Allocations capped at total budget."""
        dist = ResourceDistributor()
        t1 = MagicMock()
        eligible = [(t1, 100)]
        allocations = dist._allocate_proportional(eligible, 5, 100)

        alloc_dict = {t: a for t, a in allocations}
        self.assertEqual(alloc_dict[t1], 5)

    def test_headroom_caps_allocation(self):
        """Allocations capped at target headroom."""
        dist = ResourceDistributor()
        t1 = MagicMock()
        t2 = MagicMock()
        eligible = [(t1, 2), (t2, 2)]
        # Budget 10 but headroom only 4 total
        allocations = dist._allocate_proportional(eligible, 10, 4)

        total = sum(a for _, a in allocations)
        self.assertLessEqual(total, 4)


class TestAlternatingDirection(EvenniaTest):

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.spawn.distributors.base.delay")
    def test_direction_flips_each_tick(self, mock_delay):
        """tick_direction alternates after each tick."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(2)

        self.assertTrue(bs.tick_direction)
        # Simulate distribute — it schedules 2 ticks
        dist.distribute(1, bs)
        self.assertEqual(mock_delay.call_count, 2)


class TestDripFeedScheduling(EvenniaTest):

    def create_script(self):
        pass

    @patch("blockchain.xrpl.services.spawn.distributors.base.delay")
    def test_single_unit_single_tick(self, mock_delay):
        """Budget of 1 → 1 tick."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(1)
        dist.distribute(1, bs)
        self.assertEqual(mock_delay.call_count, 1)

    @patch("blockchain.xrpl.services.spawn.distributors.base.delay")
    def test_twelve_units_twelve_ticks(self, mock_delay):
        """Budget of 12 → 12 ticks (max)."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(12)
        dist.distribute(1, bs)
        self.assertEqual(mock_delay.call_count, 12)

    @patch("blockchain.xrpl.services.spawn.distributors.base.delay")
    def test_capped_at_twelve_ticks(self, mock_delay):
        """Budget of 30 → 12 ticks (capped)."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(30)
        dist.distribute(1, bs)
        self.assertEqual(mock_delay.call_count, 12)

    @patch("blockchain.xrpl.services.spawn.distributors.base.delay")
    def test_tick_amounts_sum_to_budget(self, mock_delay):
        """All tick amounts sum to total budget."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(25)
        dist.distribute(1, bs)

        # Extract tick_amount from delay calls
        # delay(delay_secs, callback, type_key, tick_amount, budget_state, is_final)
        total = sum(
            call_args[0][3]  # args[3] is tick_amount
            for call_args in mock_delay.call_args_list
        )
        self.assertEqual(total, 25)

    @patch("blockchain.xrpl.services.spawn.distributors.base.delay")
    def test_tick_intervals(self, mock_delay):
        """Ticks spaced evenly across the hour."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(4)
        dist.distribute(1, bs)

        delays = [call_args[0][0] for call_args in mock_delay.call_args_list]
        # 4 ticks → interval 900s
        self.assertAlmostEqual(delays[0], 0.0)
        self.assertAlmostEqual(delays[1], 900.0)
        self.assertAlmostEqual(delays[2], 1800.0)
        self.assertAlmostEqual(delays[3], 2700.0)


class TestSurplusBanking(EvenniaTest):

    def create_script(self):
        pass

    def test_surplus_banked_when_no_targets(self):
        """Budget surplus banked when no targets available."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(10)

        # Simulate a tick with no targets
        with patch.object(dist, "_query_targets", return_value=[]):
            dist._apply_tick(1, 5, bs, is_final=False)

        self.assertEqual(bs.surplus_bank, 5)

    def test_surplus_dropped_at_final_tick(self):
        """Surplus dropped and logged at final tick."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(10)

        with patch.object(dist, "_query_targets", return_value=[]):
            dist._apply_tick(1, 5, bs, is_final=True)

        self.assertEqual(bs.dropped_this_hour, 5)
        self.assertEqual(bs.surplus_bank, 0)
