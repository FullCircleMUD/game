"""
Quest debt — applying a reward already given to the spawn budget.

A quest that hands a player 50 gold does not create it: that 50 is deducted
from what the spawn system would otherwise place in the world, so rewards
redirect supply rather than adding to it.

The budget lives on whichever process runs the spawn service — the router
under sharding — but quests complete wherever the player is. This module is
the receiving end of that hop: a shard posts a `spawn_quest_debt` message,
the router's handler unpacks it here, and it lands in the same
`allocate_quest_reward()` the monolith path calls directly.

Two properties worth knowing, both accepted rather than defended against:

- **Late is fine.** If the router is down the row simply waits in Postgres
  and is processed on recovery. `allocate_quest_reward()` creates a
  BudgetState when none exists, and `reset_for_hour()` deliberately
  preserves `quest_debt`, so debt arriving before or between cycles is
  banked rather than lost.
- **Delivery is at-least-once.** A redelivered message would count the debt
  twice, and unlike placements there is no clamp to bound that. The effect
  is *less* spawning for one cycle, which in a system built around scarcity
  is the harmless direction, and the next saturation reading absorbs it.
"""

QUEST_DEBT_KIND = "spawn_quest_debt"


def apply_quest_debt(payload):
    """Apply a debt message to the running spawn service's budget.

    Args:
        payload: {"category": str, "key": str, "amount": int}

    Returns:
        bool — True if the debt was registered.
    """
    from blockchain.xrpl.services.spawn.log import spawn_log
    from blockchain.xrpl.services.spawn.service import get_spawn_service

    payload = payload or {}
    category = payload.get("category")
    key = payload.get("key")
    amount = payload.get("amount")

    if not category or key is None or not amount:
        spawn_log(f"quest debt: malformed payload {payload!r}", level="WARN")
        return False

    service = get_spawn_service()
    if not service:
        spawn_log(
            f"quest debt {category}/{key} x{amount} dropped — no spawn "
            f"service running on this process",
            level="ERROR",
        )
        return False

    service.allocate_quest_reward(category, key, amount)
    spawn_log(f"quest debt applied: {category}/{key} x{amount}")
    return True
