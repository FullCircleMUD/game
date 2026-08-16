"""Tests for spawn/planner.py — deciding a tick's placements.

The planner is the decide half of a drip-feed tick: it reads headroom,
allocates the tick's budget across eligible targets, and returns placements
for an executor to carry out. It places nothing itself.

Real objects throughout, so the reader underneath does genuine work — these
would pass against a broken query if the targets were mocked.

evennia test --settings settings tests.spawn_tests.test_planner
"""

import json
from unittest.mock import patch

from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest

from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.planner import plan_tick

RESOURCE_ID = 1
TAG = "spawn_resources"
QUERY_TARGETS = "blockchain.xrpl.services.spawn.planner.query_targets"


def _make_target(key="Target", capacity=None, current=None):
    """A real tagged object with a resource cap and optional held amount."""
    obj = create.create_object(
        "evennia.objects.objects.DefaultObject", key=key, nohome=True,
    )
    obj.tags.add(TAG, category=TAG)
    if capacity is not None:
        obj.attributes.add("spawn_resources_max", {RESOURCE_ID: capacity})
    if current is not None:
        obj.attributes.add("resources", {RESOURCE_ID: current})
    return obj


def _budget(total=10):
    bs = BudgetState(item_type="resource", type_key=RESOURCE_ID)
    bs.reset_for_hour(total)
    return bs


def _plan(bs, tick_amount, is_final=False):
    return plan_tick(
        "resources", TAG, RESOURCE_ID, tick_amount, bs, is_final,
    )


# ================================================================== #
#  The payload crossing the pipeline
# ================================================================== #


class TestPlacementShape(EvenniaTest):
    """The placement dict is the contract between planner, dispatcher and
    executor, and it travels over the message bus as JSON."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_placement_keys(self):
        _make_target(capacity=5)
        placements = _plan(_budget(), 3)
        self.assertEqual(len(placements), 1)
        self.assertEqual(
            set(placements[0]),
            {"category", "type_key", "target_pk", "amount", "shard_id"},
        )

    def test_placement_carries_its_owning_shard(self):
        """Routing information, gathered during target discovery so the
        dispatcher needs no second lookup.

        Mode-aware: None under `settings` (no shard_id column), the real
        owner under `settings_shard0`.
        """
        from evennia_shards import ROLE_MONOLITH, get_role, get_shard_id

        _make_target(capacity=5)
        placements = _plan(_budget(), 3)
        if get_role() == ROLE_MONOLITH:
            self.assertIsNone(placements[0]["shard_id"])
        else:
            self.assertEqual(placements[0]["shard_id"], get_shard_id())

    def test_placement_carries_its_own_category(self):
        """Entries are self-describing so a message can mix items, and the
        executor can pick a distributor without an envelope."""
        _make_target(capacity=5)
        placements = _plan(_budget(), 3)
        self.assertEqual(placements[0]["category"], "resources")

    def test_placement_values(self):
        target = _make_target(capacity=5)
        placements = _plan(_budget(), 3)
        self.assertEqual(placements[0]["type_key"], RESOURCE_ID)
        self.assertEqual(placements[0]["target_pk"], target.pk)
        self.assertEqual(placements[0]["amount"], 3)

    def test_payload_is_json_serialisable(self):
        _make_target(capacity=5)
        placements = _plan(_budget(), 3)
        self.assertEqual(json.loads(json.dumps(placements)), placements)

    def test_no_targets_returns_empty_list(self):
        self.assertEqual(_plan(_budget(), 3), [])


# ================================================================== #
#  Headroom is capacity minus what is already held
# ================================================================== #


class TestHeadroom(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_existing_items_reduce_available_room(self):
        """Capacity 10 holding 4 leaves room for 6, not 10."""
        _make_target(capacity=10, current=4)
        placements = _plan(_budget(50), 50)
        self.assertEqual(placements[0]["amount"], 6)

    def test_full_target_receives_nothing(self):
        _make_target(capacity=5, current=5)
        self.assertEqual(_plan(_budget(), 3), [])

    def test_overfull_target_receives_nothing(self):
        """Negative headroom must not be treated as capacity."""
        _make_target(capacity=5, current=9)
        self.assertEqual(_plan(_budget(), 3), [])

    def test_target_without_capacity_excluded(self):
        _make_target(key="NoCap")
        self.assertEqual(_plan(_budget(), 3), [])

    def test_only_targets_with_room_included(self):
        full = _make_target("Full", capacity=2, current=2)
        open_ = _make_target("Open", capacity=5)
        placements = _plan(_budget(), 3)
        pks = [p["target_pk"] for p in placements]
        self.assertIn(open_.pk, pks)
        self.assertNotIn(full.pk, pks)


# ================================================================== #
#  Quest debt
# ================================================================== #


class TestQuestDebt(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_debt_reduces_effective_budget(self):
        _make_target(capacity=20)
        bs = _budget()
        bs.add_quest_debt(4)
        placements = _plan(bs, 10)
        self.assertEqual(placements[0]["amount"], 6)

    def test_debt_fully_absorbing_tick_does_no_queries(self):
        """Settling debt before reading means a consumed tick is free."""
        bs = _budget()
        bs.add_quest_debt(100)
        with patch(QUERY_TARGETS) as mock_query:
            placements = _plan(bs, 10)
        mock_query.assert_not_called()
        self.assertEqual(placements, [])

    def test_debt_is_consumed_not_reapplied(self):
        _make_target(capacity=50)
        bs = _budget(100)
        bs.add_quest_debt(4)
        _plan(bs, 10)
        self.assertEqual(bs.quest_debt, 0)


# ================================================================== #
#  Direction alternates every tick, including on the early exits
# ================================================================== #


class TestDirectionAlternates(EvenniaTest):
    """Sort direction decides who absorbs rounding remainders. It must flip
    on every tick, or one end of the capacity range is favoured all hour."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_flips_on_normal_tick(self):
        _make_target(capacity=5)
        bs = _budget()
        before = bs.tick_direction
        _plan(bs, 3)
        self.assertNotEqual(bs.tick_direction, before)

    def test_flips_when_budget_absorbed_by_debt(self):
        bs = _budget()
        bs.add_quest_debt(100)
        before = bs.tick_direction
        _plan(bs, 3)
        self.assertNotEqual(bs.tick_direction, before)

    def test_flips_when_no_targets(self):
        bs = _budget()
        before = bs.tick_direction
        _plan(bs, 3)
        self.assertNotEqual(bs.tick_direction, before)

    def test_flips_when_all_targets_full(self):
        _make_target(capacity=2, current=2)
        bs = _budget()
        before = bs.tick_direction
        _plan(bs, 3)
        self.assertNotEqual(bs.tick_direction, before)


# ================================================================== #
#  Unplaceable budget: banked mid-hour, dropped at the end
# ================================================================== #


class TestBankOrDrop(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_no_targets_banks_mid_hour(self):
        bs = _budget()
        _plan(bs, 5)
        self.assertEqual(bs.surplus_bank, 5)
        self.assertEqual(bs.dropped_this_hour, 0)

    def test_no_targets_drops_at_final_tick(self):
        bs = _budget()
        _plan(bs, 5, is_final=True)
        self.assertEqual(bs.dropped_this_hour, 5)
        self.assertEqual(bs.surplus_bank, 0)

    def test_all_full_banks_mid_hour(self):
        _make_target(capacity=2, current=2)
        bs = _budget()
        _plan(bs, 5)
        self.assertEqual(bs.surplus_bank, 5)

    def test_all_full_drops_at_final_tick(self):
        _make_target(capacity=2, current=2)
        bs = _budget()
        _plan(bs, 5, is_final=True)
        self.assertEqual(bs.dropped_this_hour, 5)

    def test_partial_placement_banks_the_rest(self):
        """Room for 2 of a 5-unit tick — the other 3 carry forward."""
        _make_target(capacity=2)
        bs = _budget()
        _plan(bs, 5)
        self.assertEqual(bs.surplus_bank, 3)

    def test_partial_placement_drops_the_rest_at_final_tick(self):
        _make_target(capacity=2)
        bs = _budget()
        _plan(bs, 5, is_final=True)
        self.assertEqual(bs.dropped_this_hour, 3)

    def test_banked_surplus_is_spent_next_tick(self):
        """Banking is not just bookkeeping — it returns to the budget."""
        _make_target(capacity=100)
        bs = _budget(100)
        with patch(QUERY_TARGETS, return_value=[]):
            _plan(bs, 5)
        self.assertEqual(bs.surplus_bank, 5)
        placements = _plan(bs, 5)
        self.assertEqual(placements[0]["amount"], 10)

    def test_banked_surplus_pays_down_quest_debt(self):
        """Banked surplus is spendable budget, so debt consumes it rather
        than it being dropped. 3 this tick plus 7 banked services 10 of the
        outstanding debt."""
        bs = _budget()
        bs.bank_surplus(7)
        bs.add_quest_debt(100)
        _plan(bs, 3, is_final=True)
        self.assertEqual(bs.surplus_bank, 0)
        self.assertEqual(bs.quest_debt, 90)
        self.assertEqual(bs.dropped_this_hour, 0)


# ================================================================== #
#  Accounting: dispatched, not placed
# ================================================================== #


class TestDispatchAccounting(EvenniaTest):
    """The planner counts what it handed out. It never learns what an
    executor actually managed to place, and does not wait to find out."""

    databases = "__all__"

    def create_script(self):
        pass

    def test_records_the_amount_allocated(self):
        _make_target(capacity=10)
        bs = _budget()
        placements = _plan(bs, 4)
        self.assertEqual(bs.dispatched_this_hour, 4)
        self.assertEqual(
            bs.dispatched_this_hour,
            sum(p["amount"] for p in placements),
        )

    def test_accumulates_across_ticks(self):
        _make_target(capacity=100)
        bs = _budget(100)
        _plan(bs, 3)
        _plan(bs, 4)
        self.assertEqual(bs.dispatched_this_hour, 7)

    def test_records_nothing_when_no_targets(self):
        bs = _budget()
        _plan(bs, 5)
        self.assertEqual(bs.dispatched_this_hour, 0)


# ================================================================== #
#  Several targets
# ================================================================== #


class TestMultipleTargets(EvenniaTest):

    databases = "__all__"

    def create_script(self):
        pass

    def test_budget_split_across_targets(self):
        _make_target("A", capacity=10)
        _make_target("B", capacity=10)
        placements = _plan(_budget(), 10)
        self.assertEqual(len(placements), 2)
        self.assertEqual(sum(p["amount"] for p in placements), 10)

    def test_no_target_exceeds_its_own_room(self):
        _make_target("Small", capacity=1)
        _make_target("Large", capacity=20)
        placements = {
            p["target_pk"]: p["amount"] for p in _plan(_budget(30), 30)
        }
        for pk, amount in placements.items():
            self.assertLessEqual(amount, 20)
        self.assertLessEqual(min(placements.values()), 1)

    def test_each_target_appears_once(self):
        for i in range(4):
            _make_target(f"T{i}", capacity=5)
        placements = _plan(_budget(), 7)
        pks = [p["target_pk"] for p in placements]
        self.assertEqual(len(pks), len(set(pks)))
