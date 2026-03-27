"""Tests for BudgetState dataclass."""

from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.budget import BudgetState


class TestBudgetState(EvenniaTest):

    def create_script(self):
        pass

    def test_reset_for_hour(self):
        """reset_for_hour sets total/remaining and clears telemetry."""
        bs = BudgetState(item_type="resource", type_key=1)
        bs.quest_debt = 5
        bs.surplus_bank = 3
        bs.spawned_this_hour = 10
        bs.dropped_this_hour = 2

        bs.reset_for_hour(50)

        self.assertEqual(bs.total, 50)
        self.assertEqual(bs.remaining, 50)
        self.assertEqual(bs.surplus_bank, 0)
        self.assertEqual(bs.spawned_this_hour, 0)
        self.assertEqual(bs.dropped_this_hour, 0)
        # Quest debt preserved across hours
        self.assertEqual(bs.quest_debt, 5)

    def test_effective_tick_budget_no_debt(self):
        """No quest debt — full tick amount returned."""
        bs = BudgetState(item_type="resource", type_key=1)
        self.assertEqual(bs.effective_tick_budget(10), 10)

    def test_effective_tick_budget_partial_debt(self):
        """Quest debt partially consumed in one tick."""
        bs = BudgetState(item_type="resource", type_key=1, quest_debt=3)
        result = bs.effective_tick_budget(10)
        self.assertEqual(result, 7)
        self.assertEqual(bs.quest_debt, 0)

    def test_effective_tick_budget_exceeding_debt(self):
        """Quest debt exceeds tick amount — effective is 0, debt reduced."""
        bs = BudgetState(item_type="resource", type_key=1, quest_debt=30)
        result = bs.effective_tick_budget(8)
        self.assertEqual(result, 0)
        self.assertEqual(bs.quest_debt, 22)

    def test_effective_tick_budget_with_surplus(self):
        """Surplus bank added to tick amount before debt."""
        bs = BudgetState(
            item_type="resource", type_key=1,
            quest_debt=5, surplus_bank=3,
        )
        result = bs.effective_tick_budget(8)
        # available = 8 + 3 = 11, debt = 5 → effective = 6
        self.assertEqual(result, 6)
        self.assertEqual(bs.quest_debt, 0)
        self.assertEqual(bs.surplus_bank, 0)

    def test_effective_tick_budget_debt_exceeds_with_surplus(self):
        """Quest debt exceeds tick + surplus — effective is 0."""
        bs = BudgetState(
            item_type="resource", type_key=1,
            quest_debt=30, surplus_bank=5,
        )
        result = bs.effective_tick_budget(8)
        # available = 8 + 5 = 13, debt = 30 → effective = 0, debt = 17
        self.assertEqual(result, 0)
        self.assertEqual(bs.quest_debt, 17)
        self.assertEqual(bs.surplus_bank, 0)

    def test_multi_tick_debt_absorption(self):
        """Large quest debt absorbed across multiple ticks."""
        bs = BudgetState(item_type="gold", type_key="gold", quest_debt=30)

        # Simulate 4 ticks of 8
        results = []
        for _ in range(4):
            results.append(bs.effective_tick_budget(8))

        self.assertEqual(results, [0, 0, 0, 2])
        self.assertEqual(bs.quest_debt, 0)

    def test_add_quest_debt(self):
        """add_quest_debt accumulates."""
        bs = BudgetState(item_type="gold", type_key="gold")
        bs.add_quest_debt(5)
        bs.add_quest_debt(3)
        self.assertEqual(bs.quest_debt, 8)

    def test_add_quest_debt_zero(self):
        """add_quest_debt ignores zero/negative."""
        bs = BudgetState(item_type="gold", type_key="gold")
        bs.add_quest_debt(0)
        bs.add_quest_debt(-5)
        self.assertEqual(bs.quest_debt, 0)

    def test_bank_surplus(self):
        """bank_surplus accumulates."""
        bs = BudgetState(item_type="resource", type_key=1)
        bs.bank_surplus(5)
        bs.bank_surplus(3)
        self.assertEqual(bs.surplus_bank, 8)

    def test_record_placed(self):
        """record_placed accumulates."""
        bs = BudgetState(item_type="resource", type_key=1)
        bs.record_placed(5)
        bs.record_placed(3)
        self.assertEqual(bs.spawned_this_hour, 8)

    def test_record_dropped(self):
        """record_dropped accumulates."""
        bs = BudgetState(item_type="resource", type_key=1)
        bs.record_dropped(2)
        bs.record_dropped(1)
        self.assertEqual(bs.dropped_this_hour, 3)

    def test_flip_direction(self):
        """flip_direction alternates True/False."""
        bs = BudgetState(item_type="resource", type_key=1)
        self.assertTrue(bs.tick_direction)
        bs.flip_direction()
        self.assertFalse(bs.tick_direction)
        bs.flip_direction()
        self.assertTrue(bs.tick_direction)
