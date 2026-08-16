"""
Planner — decides where a tick's budget goes, without placing anything.

This is the decide half of what used to be BaseDistributor._apply_tick. It
runs on the router: read every eligible target's headroom, allocate the
tick's budget across them, and return a list of placements for someone else
to carry out. The place half is the executor, which runs on whichever shard
owns each target.

Splitting the two is what makes the sharded deployment possible, but the
decisions themselves are unchanged — same late-bound target discovery, same
headroom filter, same alternating sort direction, same proportional
allocation, same surplus banking.

Output is a list of placement dicts:

    {"category": <str>, "type_key": <str|int>,
     "target_pk": <int>, "amount": <int>}

Plain JSON-serialisable data, because it crosses the message bus. Each entry
is self-describing — carrying its own category rather than relying on the
envelope — so placements for different items can share one message, and the
executor can dispatch each to the right distributor.

**One deliberate behaviour change.** The old code counted what it actually
placed, because it placed things itself and could see failures. The router
cannot: dispatch is fire-and-forget, and shards do not report back. So
`record_dispatched()` here counts what was *dispatched*, and a placement the
shard later declines is not banked for retry within the hour. That budget is
not lost so much as deferred — the next hourly saturation and telemetry
snapshots measure the world as it actually is, so a shortfall reappears as
budget in the following cycle. See docs/unified-item-spawn-system.md
§ Multi-Shard Distribution Architecture.
"""

from blockchain.xrpl.services.spawn.allocator import allocate
from blockchain.xrpl.services.spawn.log import spawn_log
from blockchain.xrpl.services.spawn.reader import (
    query_targets,
    read_capacity,
    read_current,
)


def _bank_or_drop(budget_state, amount, is_final, category, type_key, reason):
    """Carry an unplaceable amount forward, or write it off at end of hour.

    Mid-hour the amount banks into the next tick. On the final tick there is
    no next tick, so it is dropped and logged — persistent drops mean the
    world needs more targets or higher per-target caps.
    """
    if amount <= 0:
        return
    if is_final:
        budget_state.record_dropped(amount)
        spawn_log(f"drop: {category}/{type_key} dropped {amount} ({reason})")
    else:
        budget_state.bank_surplus(amount)
        spawn_log(f"bank: {category}/{type_key} banked {amount} ({reason})")


def plan_tick(category, tag_name, type_key, tick_amount, budget_state, is_final):
    """Decide this tick's placements for one spawnable item.

    Args:
        category: "resources", "gold", "scrolls", "recipes" or "nfts".
        tag_name: the spawn tag identifying eligible targets,
            e.g. "spawn_resources".
        type_key: resource_id, "gold", or item key.
        tick_amount: this tick's share of the hourly budget.
        budget_state: BudgetState for this item. Mutated — quest debt is
            consumed, surplus banked or dropped, direction flipped.
        is_final: True on the last tick of the hour.

    Returns:
        list[dict] — placements, possibly empty.
    """
    # Quest debt and banked surplus are settled before anything is read, so
    # a tick fully consumed by debt costs no queries. Note that
    # effective_tick_budget() folds the banked surplus into what it returns
    # and zeroes the bank, so there is never a leftover bank to write off
    # here — an unplaceable amount is dropped further down, by _bank_or_drop.
    effective = budget_state.effective_tick_budget(tick_amount)
    spawn_log(
        f"plan: {category}/{type_key} tick={tick_amount} final={is_final} "
        f"effective={effective} debt={budget_state.quest_debt}"
    )
    if effective <= 0:
        budget_state.flip_direction()
        return []

    # Late-bound: targets are discovered now, not when the tick was
    # scheduled, so mobs that died or rooms that were harvested since are
    # reflected.
    shard_by_pk = query_targets(tag_name)
    target_pks = list(shard_by_pk)
    if not target_pks:
        _bank_or_drop(
            budget_state, effective, is_final, category, type_key,
            "no targets",
        )
        budget_state.flip_direction()
        return []

    capacity = read_capacity(target_pks, category, type_key)
    current = read_current(target_pks, category, type_key)

    eligible = []
    for pk in target_pks:
        headroom = capacity.get(pk, 0) - current.get(pk, 0)
        if headroom > 0:
            eligible.append((pk, headroom))

    if not eligible:
        _bank_or_drop(
            budget_state, effective, is_final, category, type_key,
            "all targets full",
        )
        budget_state.flip_direction()
        return []

    # Direction alternates each tick so integer rounding does not always
    # favour the same end of the capacity range: high-capacity targets
    # (chests, rich veins) one tick, low-capacity ones (mobs) the next.
    eligible.sort(key=lambda pair: pair[1], reverse=budget_state.tick_direction)

    total_headroom = sum(headroom for _, headroom in eligible)
    allocations = allocate(eligible, effective, total_headroom)

    dispatched = sum(amount for _, amount in allocations)
    spawn_log(
        f"plan: {category}/{type_key} {len(target_pks)} target(s), "
        f"{len(eligible)} eligible, headroom={total_headroom}, "
        f"dispatched={dispatched} to {len(allocations)} target(s)"
    )
    budget_state.record_dispatched(dispatched)

    _bank_or_drop(
        budget_state, effective - dispatched, is_final, category, type_key,
        "surplus",
    )

    budget_state.flip_direction()

    return [
        {
            "category": category,
            "type_key": type_key,
            "target_pk": pk,
            "amount": amount,
            # Carried from the target discovery query, so the dispatcher can
            # route without looking ownership up again. None in monolith.
            "shard_id": shard_by_pk.get(pk),
        }
        for pk, amount in allocations
    ]
