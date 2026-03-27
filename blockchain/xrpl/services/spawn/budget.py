"""
BudgetState — mutable per-item budget tracked across drip-feed ticks.

Lives on the SpawnService instance so both drip-feed callbacks and
the quest reward system can access it.
"""

from dataclasses import dataclass, field


@dataclass
class BudgetState:
    """Mutable hourly budget for a single spawnable item."""

    item_type: str          # "resource", "gold", "knowledge", "rare_nft"
    type_key: str | int     # resource_id, "gold", or item_type_name

    total: int = 0          # total hourly budget from calculator
    remaining: int = 0      # what hasn't been scheduled yet
    quest_debt: int = 0     # deducted from upcoming ticks
    surplus_bank: int = 0   # carried from previous tick
    tick_direction: bool = True  # True = high→low, False = low→high

    # Telemetry counters
    spawned_this_hour: int = 0
    dropped_this_hour: int = 0

    def reset_for_hour(self, total: int):
        """Reset budget for a new hourly cycle. Preserves quest_debt."""
        self.total = total
        self.remaining = total
        self.surplus_bank = 0
        self.tick_direction = True
        self.spawned_this_hour = 0
        self.dropped_this_hour = 0

    def effective_tick_budget(self, tick_amount: int) -> int:
        """Calculate effective budget for a tick after quest debt.

        Returns the amount available for distribution. Updates quest_debt.
        """
        available = tick_amount + self.surplus_bank
        self.surplus_bank = 0

        if self.quest_debt > 0:
            deduction = min(available, self.quest_debt)
            available -= deduction
            self.quest_debt -= deduction

        return max(0, available)

    def add_quest_debt(self, amount: int):
        """Register quest reward debt against this item's budget."""
        if amount > 0:
            self.quest_debt += amount

    def bank_surplus(self, surplus: int):
        """Bank unplaceable items for the next tick."""
        if surplus > 0:
            self.surplus_bank += surplus

    def record_placed(self, amount: int):
        """Record items actually placed this tick."""
        self.spawned_this_hour += amount

    def record_dropped(self, amount: int):
        """Record surplus dropped at end of hour."""
        self.dropped_this_hour += amount

    def flip_direction(self):
        """Alternate sort direction for next tick."""
        self.tick_direction = not self.tick_direction
