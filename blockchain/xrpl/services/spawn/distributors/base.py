"""
BaseDistributor — drip-feed scheduling and placement.

Handles:
- Drip-feed scheduling (max 12 ticks/hour)
- Executing the placements a tick decides on

Deciding *which* targets receive *how much* is not here — that is planner.py,
which reads headroom and allocates without touching game objects so it can
run on the router across every shard's targets. This class schedules the
ticks and carries out what the planner returns.
"""

import logging

from evennia.utils.utils import delay
from utils.db_threads import defer_to_db_thread

from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.planner import plan_tick

logger = logging.getLogger("evennia")

# Maximum drip-feed ticks per hour (every 5 minutes minimum).
MAX_TICKS_PER_HOUR = 12


class BaseDistributor:
    """Shared distribution logic for all spawn categories."""

    # Subclasses set these
    tag_name = None        # e.g. "spawn_resources"
    tag_category = None    # e.g. "spawn" (optional, for Evennia tag filtering)
    category = None        # e.g. "resources", "gold", "scrolls", "recipes", "nfts"
    max_attr_name = None   # e.g. "spawn_resources_max"

    def distribute(self, type_key, budget_state):
        """Schedule drip-feed distribution for one item over the hour.

        Args:
            type_key: resource_id, "gold", or item_type_name
            budget_state: BudgetState instance for this item
        """
        total = budget_state.remaining
        if total <= 0:
            return

        num_ticks = min(total, MAX_TICKS_PER_HOUR)
        interval = 3600.0 / num_ticks
        per_tick_base = total // num_ticks
        extra = total % num_ticks

        for i in range(num_ticks):
            tick_amount = per_tick_base + (1 if i < extra else 0)
            delay_seconds = i * interval
            is_final = (i == num_ticks - 1)
            delay(
                delay_seconds,
                self._apply_tick,
                type_key, tick_amount, budget_state, is_final,
            )

        budget_state.remaining = 0

    def _apply_tick(self, type_key, tick_amount, budget_state, is_final):
        """Single drip-feed tick — decide placements, then route them.

        `delay()` schedules onto the reactor, so this starts there. On the
        router the work is moved off it: reading every tagged target's
        headroom across the cluster is not something to do in front of
        someone sitting at character select. Everything the router does is
        ORM-only — no `.db` access, no typeclass instances — and Django is
        connection-per-thread, so a worker thread is safe.

        In monolith it stays on the reactor, because dispatch resolves
        straight to the executor and placement writes Evennia attributes and
        creates objects. That must happen on the reactor thread.

        Args:
            type_key: resource_id, "gold", or item_type_name
            tick_amount: base amount for this tick
            budget_state: BudgetState instance
            is_final: True on the last tick of the hour
        """
        from evennia_shards import ROLE_MONOLITH, get_role

        if get_role() == ROLE_MONOLITH:
            self._run_tick(type_key, tick_amount, budget_state, is_final)
            return

        defer_to_db_thread(
            self._run_tick, type_key, tick_amount, budget_state, is_final,
        )

    def _run_tick(self, type_key, tick_amount, budget_state, is_final):
        """Decide and route one tick's placements."""
        # Imported here rather than at module scope: the dispatcher reaches
        # the executor, which imports the distributor subclasses, which
        # import this module.
        from blockchain.xrpl.services.spawn.dispatcher import dispatch

        placements = plan_tick(
            self.category, self.tag_name, type_key,
            tick_amount, budget_state, is_final,
        )
        dispatch(placements)

    def _place(self, target, type_key, amount):
        """Place items on a target. Subclasses must implement."""
        raise NotImplementedError
