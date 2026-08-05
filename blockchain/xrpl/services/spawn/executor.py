"""
Executor — carries out planned placements on the shard that owns the targets.

The planner decides *what* should go *where* and produces a list of
placements. This module carries them out. In a sharded deployment the two
run in different processes, with the list travelling over the message bus;
in monolith they run back to back in one. The code path is the same either
way.

Each placement is self-describing:

    {"category": "resources", "type_key": 1, "target_pk": 42, "amount": 3}

``category`` selects the distributor, since placing gold, a resource and a
scroll are entirely different operations. The other three fields are exactly
the arguments every ``_place`` implementation already takes, with the target
given as a pk rather than an instance — because only the owning shard may
resolve it.

Two guards sit between receiving a placement and acting on it, covering the
second or so that passes between the planner reading the world and this
running:

- **The target may be gone.** Mobs die, containers are removed. A pk that no
  longer resolves is skipped. Note that on a shard the tenant auto-filter
  means a pk belonging to a *different* shard also fails to resolve, so a
  misrouted message is caught by the same lookup.
- **The headroom may have closed.** Re-checked immediately before placing and
  the amount clamped to what still fits. This is what makes at-least-once
  delivery safe: a duplicate message finds no room and places nothing, so no
  per-message dedup record is needed.

In practice neither should fire. Everything that plausibly changes in that
window — a mob dying, a room being harvested, a chest looted — *increases*
headroom. The guards exist for the unexpected.

Entries are isolated: a malformed entry, an unknown category, a vanished
target or a failed placement affects only itself. One bad scroll must not
cost the gold in the same message.
"""

import traceback
from collections import defaultdict

from blockchain.xrpl.services.spawn.distributors.fungible import (
    GoldDistributor,
    ResourceDistributor,
)
from blockchain.xrpl.services.spawn.distributors.nft import (
    RareNFTDistributor,
    RecipeDistributor,
    ScrollDistributor,
)
from blockchain.xrpl.services.spawn.log import spawn_log
from blockchain.xrpl.services.spawn.reader import read_capacity, read_current

# Distributors hold no per-call state — only class attributes — so one
# instance each is enough.
_DISTRIBUTORS = {
    "resources": ResourceDistributor(),
    "gold": GoldDistributor(),
    "scrolls": ScrollDistributor(),
    "recipes": RecipeDistributor(),
    "nfts": RareNFTDistributor(),
}

_REQUIRED_FIELDS = ("category", "type_key", "target_pk", "amount")


def execute(placements):
    """Carry out a list of planned placements.

    Args:
        placements: list of placement dicts, in any mix of categories.

    Returns:
        int — units placed. Approximate for NFT categories, where each unit
        is a separate token allocation and a failure partway through leaves
        earlier units in place; those are not counted.
    """
    total = 0
    for (category, type_key), group in _group_by_item(placements).items():
        try:
            total += _execute_group(category, type_key, group)
        except Exception:
            spawn_log(
                f"execute: group {category}/{type_key} failed entirely\n"
                f"{traceback.format_exc()}",
                level="ERROR",
            )
    spawn_log(f"execute: {len(placements)} placements -> {total} units placed")
    return total


def _group_by_item(placements):
    """Group valid placements by (category, type_key).

    Grouping keeps the headroom re-check to one pair of queries per item
    rather than one pair per placement.
    """
    grouped = defaultdict(list)
    for placement in placements:
        if not isinstance(placement, dict) or any(
            field not in placement for field in _REQUIRED_FIELDS
        ):
            spawn_log(
                f"execute: malformed placement {placement!r}", level="WARN",
            )
            continue
        category = placement["category"]
        if category not in _DISTRIBUTORS:
            spawn_log(
                f"execute: unknown category {category!r} in {placement!r}",
                level="WARN",
            )
            continue
        grouped[(category, placement["type_key"])].append(placement)
    return grouped


def _execute_group(category, type_key, placements):
    """Place every entry for one item, clamping each to current headroom."""
    from evennia.objects.models import ObjectDB

    distributor = _DISTRIBUTORS[category]
    target_pks = [placement["target_pk"] for placement in placements]
    spawn_log(
        f"execute group: {category}/{type_key} across "
        f"{len(target_pks)} target(s)"
    )

    capacity = read_capacity(target_pks, category, type_key)
    current = read_current(target_pks, category, type_key)

    placed = 0
    for placement in placements:
        target_pk = placement["target_pk"]
        amount = placement["amount"]
        if amount <= 0:
            continue

        headroom = capacity.get(target_pk, 0) - current.get(target_pk, 0)
        if headroom <= 0:
            spawn_log(
                f"clamp: {category}/{type_key} target {target_pk} full, "
                f"dropping {amount}"
            )
            continue
        if amount > headroom:
            spawn_log(
                f"clamp: {category}/{type_key} target {target_pk} has room "
                f"for {headroom} of {amount}"
            )
            amount = headroom

        try:
            target = ObjectDB.objects.get(pk=target_pk)
        except ObjectDB.DoesNotExist:
            # Gone, or owned by another shard — the auto-filter hides both.
            spawn_log(
                f"skip: {category}/{type_key} target {target_pk} not "
                f"available on this shard"
            )
            continue

        try:
            distributor._place(target, type_key, amount)
            placed += amount
            spawn_log(f"place: {category}/{type_key} x{amount} on {target_pk}")
        except Exception:
            spawn_log(
                f"place FAILED: {category}/{type_key} x{amount} on "
                f"{target_pk}\n{traceback.format_exc()}",
                level="ERROR",
            )

    return placed
