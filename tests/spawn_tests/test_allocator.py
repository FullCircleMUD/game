"""Tests for spawn/allocator.py — proportional allocation by headroom.

The allocator is a pure function over numbers, so these are plain unit tests
with no database and no Evennia objects. Target identity is an ObjectDB pk.

Two properties get particular attention:

  - pks above CPython's small-integer interning range (-5..256). The previous
    implementation compared targets with `is`, which holds for the low pks a
    fresh test database issues and stops holding above 256. Every structural
    test here uses large pks so a regression cannot pass unnoticed.
  - behavioural equivalence with the original list-based implementation,
    checked by differential fuzzing against a reference copy kept below.

evennia test --settings settings tests.spawn_tests.test_allocator
"""

import math
import random
import unittest

from blockchain.xrpl.services.spawn.allocator import allocate


# Pks chosen above the interning range so identity comparison would fail.
PK_A, PK_B, PK_C = 40001, 40002, 40003


# ================================================================== #
#  Reference implementation
# ================================================================== #


def _reference_allocate(eligible, budget, total_headroom):
    """The original list-of-tuples algorithm from BaseDistributor.

    Preserved verbatim apart from `is` becoming `==` (identity comparison
    was only ever safe because targets were idmapper-backed objects). The
    dict implementation must agree with this for every input.
    """
    if total_headroom <= 0:
        return []

    allocations = []
    allocated = 0

    for target, headroom in eligible:
        if allocated >= budget:
            break
        raw = budget * headroom / total_headroom
        if raw < 1.0 and raw > 0:
            amount = 1
        else:
            amount = math.floor(raw)
        amount = min(amount, headroom, budget - allocated)
        if amount > 0:
            allocations.append((target, amount))
            allocated += amount

    remainder = budget - allocated
    if remainder > 0:
        for target, headroom in eligible:
            if remainder <= 0:
                break
            current_alloc = 0
            for i, (t, a) in enumerate(allocations):
                if t == target:
                    current_alloc = a
                    break
            can_add = headroom - current_alloc
            if can_add > 0:
                found = False
                for i, (t, a) in enumerate(allocations):
                    if t == target:
                        allocations[i] = (t, a + 1)
                        found = True
                        break
                if not found:
                    allocations.append((target, 1))
                remainder -= 1

    return [(t, a) for t, a in allocations if a > 0]


# ================================================================== #
#  Migrated from TestProportionalAllocation
# ================================================================== #


class TestProportionalAllocation(unittest.TestCase):
    """The four cases that covered _allocate_proportional before the move,
    retargeted from mock objects to pks."""

    def test_proportional_by_headroom(self):
        """Budget distributed proportionally by headroom."""
        eligible = [(PK_A, 10), (PK_B, 5), (PK_C, 5)]
        result = dict(allocate(eligible, 10, 20))
        # floor(10*10/20)=5, floor(10*5/20)=2, floor(10*5/20)=2 -> 9
        # remainder 1 goes to the first in order
        self.assertEqual(result[PK_A], 6)
        self.assertEqual(result[PK_B], 2)
        self.assertEqual(result[PK_C], 2)

    def test_minimum_one_allocation(self):
        """A share between 0 and 1 rounds up, so small targets aren't starved."""
        eligible = [(PK_A, 1), (PK_B, 100)]
        result = dict(allocate(eligible, 5, 101))
        # 5*1/101 ~= 0.05 -> 1 ;  5*100/101 ~= 4.95 -> floor 4
        self.assertEqual(result[PK_A], 1)
        self.assertEqual(result[PK_B], 4)

    def test_budget_caps_allocation(self):
        eligible = [(PK_A, 100)]
        self.assertEqual(dict(allocate(eligible, 5, 100))[PK_A], 5)

    def test_headroom_caps_allocation(self):
        eligible = [(PK_A, 2), (PK_B, 2)]
        total = sum(a for _, a in allocate(eligible, 10, 4))
        self.assertLessEqual(total, 4)


# ================================================================== #
#  Identity vs equality — the reason pks here are large
# ================================================================== #


class TestTargetIdentity(unittest.TestCase):

    def test_no_duplicate_entries_for_one_target(self):
        """A target must appear at most once in the result.

        With `is` comparison and pks above the interning range, the remainder
        pass fails to find the existing entry and appends a second one for the
        same target — which the caller would then place on twice, breaking the
        headroom cap.
        """
        eligible = [(PK_A, 10), (PK_B, 10)]
        result = allocate(eligible, 7, 20)
        pks = [pk for pk, _ in result]
        self.assertEqual(len(pks), len(set(pks)))

    def test_remainder_increments_rather_than_appends(self):
        """Total must equal the budget, not exceed it via duplicate entries."""
        eligible = [(PK_A, 10), (PK_B, 10), (PK_C, 10)]
        result = allocate(eligible, 11, 30)
        self.assertEqual(sum(a for _, a in result), 11)

    def test_headroom_respected_with_large_pks(self):
        eligible = [(PK_A, 3), (PK_B, 3)]
        result = dict(allocate(eligible, 6, 6))
        self.assertLessEqual(result[PK_A], 3)
        self.assertLessEqual(result[PK_B], 3)


# ================================================================== #
#  Invariants
# ================================================================== #


class TestInvariants(unittest.TestCase):

    def test_zero_total_headroom_allocates_nothing(self):
        self.assertEqual(allocate([(PK_A, 0)], 10, 0), [])

    def test_empty_eligible_allocates_nothing(self):
        self.assertEqual(allocate([], 10, 0), [])

    def test_zero_budget_allocates_nothing(self):
        self.assertEqual(allocate([(PK_A, 10)], 0, 10), [])

    def test_never_exceeds_budget(self):
        eligible = [(PK_A, 100), (PK_B, 100), (PK_C, 100)]
        total = sum(a for _, a in allocate(eligible, 7, 300))
        self.assertLessEqual(total, 7)

    def test_never_exceeds_headroom_per_target(self):
        eligible = [(PK_A, 1), (PK_B, 1), (PK_C, 1)]
        for _, amount in allocate(eligible, 50, 3):
            self.assertLessEqual(amount, 1)

    def test_surplus_left_unallocated_when_headroom_exhausted(self):
        """One remainder pass only — leftover is the caller's surplus."""
        eligible = [(PK_A, 1), (PK_B, 1)]
        total = sum(a for _, a in allocate(eligible, 100, 2))
        self.assertEqual(total, 2)

    def test_zero_amounts_are_omitted(self):
        for _, amount in allocate([(PK_A, 5), (PK_B, 5)], 3, 10):
            self.assertGreater(amount, 0)

    def test_order_follows_eligible(self):
        """Sort direction is the caller's lever for who absorbs the remainder,
        so the result must preserve the order it was given."""
        eligible = [(PK_C, 10), (PK_A, 10), (PK_B, 10)]
        result = allocate(eligible, 9, 30)
        self.assertEqual([pk for pk, _ in result], [PK_C, PK_A, PK_B])


# ================================================================== #
#  Differential fuzz against the reference implementation
# ================================================================== #


class TestMatchesReferenceImplementation(unittest.TestCase):
    """The dict form must be behaviour-preserving, not merely plausible."""

    def _compare(self, eligible, budget):
        total_headroom = sum(h for _, h in eligible)
        self.assertEqual(
            allocate(eligible, budget, total_headroom),
            _reference_allocate(eligible, budget, total_headroom),
            msg=f"diverged for eligible={eligible} budget={budget}",
        )

    def test_random_cases(self):
        rng = random.Random(20260804)
        for _ in range(2000):
            count = rng.randint(1, 8)
            # pks span the interning boundary deliberately
            pks = rng.sample(range(1, 40000), count)
            eligible = [(pk, rng.randint(0, 40)) for pk in pks]
            self._compare(eligible, rng.randint(0, 60))

    def test_remainder_heavy_cases(self):
        """Budgets just above a clean division exercise the remainder pass."""
        rng = random.Random(99)
        for _ in range(500):
            count = rng.randint(2, 6)
            headroom = rng.randint(1, 10)
            eligible = [(40000 + i, headroom) for i in range(count)]
            self._compare(eligible, count * headroom // 2 + rng.randint(1, 3))

    def test_single_target_cases(self):
        for headroom in range(0, 12):
            for budget in range(0, 12):
                self._compare([(PK_A, headroom)], budget)
