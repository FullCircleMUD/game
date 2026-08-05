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
        """Budget surplus banked when no targets available.

        Target discovery moved into the planner, so that is where the empty
        result is injected — the behaviour under test is unchanged.
        """
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(10)

        with patch(
            "blockchain.xrpl.services.spawn.planner.query_targets",
            return_value=[],
        ):
            dist._apply_tick(1, 5, bs, is_final=False)

        self.assertEqual(bs.surplus_bank, 5)

    def test_surplus_dropped_at_final_tick(self):
        """Surplus dropped and logged at final tick."""
        dist = ResourceDistributor()
        bs = BudgetState(item_type="resource", type_key=1)
        bs.reset_for_hour(10)

        with patch(
            "blockchain.xrpl.services.spawn.planner.query_targets",
            return_value=[],
        ):
            dist._apply_tick(1, 5, bs, is_final=True)

        self.assertEqual(bs.dropped_this_hour, 5)
        self.assertEqual(bs.surplus_bank, 0)
