"""
BaseDistributor — shared distribution mechanics for all spawn categories.

Handles:
- Tag-driven target pooling (single tag query + dict filter)
- Proportional allocation by headroom
- Alternating direction each tick
- Drip-feed scheduling (max 12 ticks/hour)
- Surplus banking
- get_current_count() delegation
"""

import logging
import math

from evennia.utils.utils import delay

from blockchain.xrpl.services.spawn.budget import BudgetState
from blockchain.xrpl.services.spawn.headroom import get_current_count

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
        """Single drip-feed tick — query targets, allocate, place.

        Args:
            type_key: resource_id, "gold", or item_type_name
            tick_amount: base amount for this tick
            budget_state: BudgetState instance
            is_final: True on the last tick of the hour
        """
        # Calculate effective budget after quest debt and surplus
        effective = budget_state.effective_tick_budget(tick_amount)
        if effective <= 0:
            if is_final and budget_state.surplus_bank > 0:
                budget_state.record_dropped(budget_state.surplus_bank)
                logger.info(
                    f"SpawnDrop: {self.category}/{type_key} dropped "
                    f"{budget_state.surplus_bank} surplus at end of hour"
                )
                budget_state.surplus_bank = 0
            budget_state.flip_direction()
            return

        # Late-bound target discovery
        targets = self._query_targets(type_key)
        if not targets:
            if is_final:
                budget_state.record_dropped(effective)
                logger.info(
                    f"SpawnDrop: {self.category}/{type_key} dropped "
                    f"{effective} (no targets at final tick)"
                )
            else:
                budget_state.bank_surplus(effective)
            budget_state.flip_direction()
            return

        # Calculate headroom per target
        eligible = []
        for target in targets:
            max_val = self._get_max_for_key(target, type_key)
            current = get_current_count(target, self.category, type_key)
            headroom = max(0, max_val - current)
            if headroom > 0:
                eligible.append((target, headroom))

        if not eligible:
            if is_final:
                budget_state.record_dropped(effective)
                logger.info(
                    f"SpawnDrop: {self.category}/{type_key} dropped "
                    f"{effective} (all targets full at final tick)"
                )
            else:
                budget_state.bank_surplus(effective)
            budget_state.flip_direction()
            return

        # Sort by headroom (direction alternates each tick)
        eligible.sort(
            key=lambda x: x[1],
            reverse=budget_state.tick_direction,
        )

        # Proportional allocation
        total_headroom = sum(h for _, h in eligible)
        allocations = self._allocate_proportional(
            eligible, effective, total_headroom,
        )

        # Place items
        placed = 0
        for target, amount in allocations:
            try:
                self._place(target, type_key, amount)
                placed += amount
            except Exception:
                logger.log_trace(
                    f"SpawnPlace: failed to place {self.category}/{type_key} "
                    f"x{amount} on {target}"
                )

        budget_state.record_placed(placed)

        # Bank surplus
        surplus = effective - placed
        if surplus > 0:
            if is_final:
                budget_state.record_dropped(surplus)
                logger.info(
                    f"SpawnDrop: {self.category}/{type_key} dropped "
                    f"{surplus} surplus at end of hour"
                )
            else:
                budget_state.bank_surplus(surplus)

        budget_state.flip_direction()

    def _allocate_proportional(self, eligible, budget, total_headroom):
        """Proportional allocation by headroom with remainder distribution.

        Args:
            eligible: list of (target, headroom) sorted by direction
            budget: int — available budget
            total_headroom: int — sum of all headroom

        Returns:
            list of (target, allocation) tuples
        """
        if total_headroom <= 0:
            return []

        allocations = []
        allocated = 0

        for target, headroom in eligible:
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
                allocations.append((target, amount))
                allocated += amount

        # Distribute remainder one-at-a-time in sort order
        remainder = budget - allocated
        if remainder > 0:
            for target, headroom in eligible:
                if remainder <= 0:
                    break
                # Find current allocation for this target
                current_alloc = 0
                for i, (t, a) in enumerate(allocations):
                    if t is target:
                        current_alloc = a
                        break
                can_add = headroom - current_alloc
                if can_add > 0:
                    # Check if target already in allocations
                    found = False
                    for i, (t, a) in enumerate(allocations):
                        if t is target:
                            allocations[i] = (t, a + 1)
                            found = True
                            break
                    if not found:
                        allocations.append((target, 1))
                    remainder -= 1

        return [(t, a) for t, a in allocations if a > 0]

    def _query_targets(self, type_key):
        """Query all tagged targets for this category.

        Returns list of Evennia objects with the spawn tag.
        Must be overridden by subclasses if custom filtering is needed.
        """
        from evennia.objects.models import ObjectDB

        return list(
            ObjectDB.objects.filter(
                db_tags__db_key=self.tag_name,
            )
        )

    def _get_max_for_key(self, target, type_key):
        """Get the max capacity for a specific key on a target.

        Args:
            target: Evennia object
            type_key: resource_id, "gold", or item_type_name

        Returns:
            int — max capacity for this key
        """
        max_dict = getattr(target.db, self.max_attr_name, None)
        if max_dict is None:
            return 0
        if isinstance(max_dict, int):
            # Gold: spawn_gold_max is a plain int
            return max_dict
        # Dict: {key: max, ...}
        return max_dict.get(type_key, max_dict.get(str(type_key), 0))

    def _place(self, target, type_key, amount):
        """Place items on a target. Subclasses must implement."""
        raise NotImplementedError
