"""
Allocator — divides a tick's budget across eligible targets by headroom.

A pure function over numbers. It performs no I/O, touches no database, and
never asks what a target is — callers pass whatever identity they use and get
the same identities back paired with amounts. That is what lets the same
allocation run on the router across the whole cluster's targets as it
previously ran in-process across one shard's.

Targets are identified by ObjectDB pk, and allocations are accumulated in a
dict keyed by that pk. Two consequences worth knowing:

- A target cannot appear twice in the result, by construction. The previous
  list-of-tuples form relied on comparing targets correctly to avoid
  appending a duplicate entry; with integer pks that would have been a live
  hazard, since CPython interns only small integers and identity comparison
  silently stops holding above 256 — passing on the low pks a fresh test
  database issues, failing on production's.
- Lookups are O(1), so distributing the remainder costs one pass over
  `eligible` rather than rescanning the accumulated allocations for every
  target.

Dicts preserve insertion order, so the output order matches the previous
implementation's: proportional-pass targets in `eligible` order, followed by
any target that first received a unit during remainder distribution.
"""

import math


def allocate(eligible, budget, total_headroom):
    """Divide budget across eligible targets, proportional to headroom.

    Each target's share is floored, except that a share between 0 and 1
    rounds up to 1 so small targets are not starved by rounding. Whatever
    remains after flooring is handed out one unit at a time in the order
    given, which is why the caller's sort direction matters: it decides who
    absorbs the rounding remainder.

    A single remainder pass is made. If the remainder exceeds the number of
    targets that can still take a unit, the leftover is not allocated — the
    caller banks it as surplus.

    Args:
        eligible: list of (target_pk, headroom), pre-sorted by the caller.
        budget: int — units available to distribute this tick.
        total_headroom: int — sum of every headroom in `eligible`.

    Returns:
        list of (target_pk, amount) — only targets receiving at least one
        unit. Never allocates more than a target's headroom, and never more
        than `budget` in total.
    """
    if total_headroom <= 0:
        return []

    allocations = {}
    allocated = 0

    for target_pk, headroom in eligible:
        if allocated >= budget:
            break
        # Proportional share, floored
        raw = budget * headroom / total_headroom
        # Minimum 1 if proportional share < 1 but > 0
        if raw < 1.0 and raw > 0:
            amount = 1
        else:
            amount = math.floor(raw)
        # Cap at headroom and remaining budget
        amount = min(amount, headroom, budget - allocated)
        if amount > 0:
            allocations[target_pk] = amount
            allocated += amount

    # Distribute remainder one-at-a-time in sort order
    remainder = budget - allocated
    if remainder > 0:
        for target_pk, headroom in eligible:
            if remainder <= 0:
                break
            current_alloc = allocations.get(target_pk, 0)
            if headroom - current_alloc > 0:
                allocations[target_pk] = current_alloc + 1
                remainder -= 1

    return [(pk, amount) for pk, amount in allocations.items() if amount > 0]
