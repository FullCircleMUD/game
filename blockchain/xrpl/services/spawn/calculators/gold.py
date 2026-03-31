"""
GoldCalculator — three-factor budget for gold currency.

    budget = consumption_rate × buffer × reserve_throttle

Every gold unit must be backed 1:1 by real assets. The reserve throttle
prevents spawning more gold than the vault can back — linear ramp-down
as runway shrinks below min_runway_days.
"""

import logging
from decimal import Decimal

from blockchain.xrpl.services.spawn.calculators.base import BaseCalculator

logger = logging.getLogger("evennia")


class GoldCalculator(BaseCalculator):
    """Three-factor gold spawn budget: consumption × buffer × throttle."""

    def calculate(self, item_type, type_key, **overrides):
        """Calculate hourly spawn budget for gold.

        Returns int — number of gold units to spawn this hour.
        """
        cfg = self.get_item_config(item_type, type_key, **overrides)

        # Baseline: 24h rolling average of gold sinks, floored at default
        default_rate = float(cfg["default_spawn_rate"])
        avg_consumption = self._get_avg_gold_sinks()
        base_rate = max(default_rate, float(avg_consumption))

        # Buffer: spawn slightly more than consumed
        buffer = float(cfg.get("buffer", 1.15))

        # Reserve throttle: safety valve based on vault balance
        hourly_budget_estimate = base_rate * buffer
        throttle = self._reserve_throttle(
            hourly_budget_estimate, cfg,
        )

        budget = base_rate * buffer * throttle
        return max(0, round(budget))

    # ================================================================== #
    #  Data queries
    # ================================================================== #

    @staticmethod
    def _get_avg_gold_sinks():
        """24h rolling average of gold_sinks_1h from EconomySnapshot.

        Returns Decimal.
        """
        from blockchain.xrpl.models import EconomySnapshot

        snapshots = EconomySnapshot.objects.order_by("-hour")[:24]
        values = [s.gold_sinks_1h for s in snapshots]
        if not values:
            return Decimal(0)
        return sum(values) / len(values)

    @staticmethod
    def _get_gold_reserve():
        """Get current gold RESERVE balance from FungibleGameState.

        Returns Decimal.
        """
        from blockchain.xrpl.models import FungibleGameState
        from django.db.models import Sum

        result = (
            FungibleGameState.objects.filter(
                currency_code="FCMGold",
                location=FungibleGameState.LOCATION_RESERVE,
            ).aggregate(total=Sum("balance"))["total"]
        )
        return result or Decimal(0)

    # ================================================================== #
    #  Reserve throttle
    # ================================================================== #

    @staticmethod
    def _reserve_throttle(hourly_budget, config):
        """Calculate reserve throttle — linear ramp-down as runway shrinks.

        Args:
            hourly_budget: estimated hourly spawn (before throttle)
            config: item config with "min_runway_days"

        Returns:
            float — 0.0 to 1.0
        """
        if hourly_budget <= 0:
            return 1.0

        min_runway = float(config.get("min_runway_days", 7))
        vault_reserve = float(GoldCalculator._get_gold_reserve())

        daily_burn = hourly_budget * 24
        if daily_burn <= 0:
            return 1.0

        runway_days = vault_reserve / daily_burn

        if runway_days >= min_runway:
            return 1.0
        elif runway_days <= 0:
            return 0.0
        else:
            return runway_days / min_runway
