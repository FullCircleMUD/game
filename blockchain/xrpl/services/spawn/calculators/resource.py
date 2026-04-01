"""
ResourceCalculator — two-factor budget for raw gathering resources.

    budget = consumption_rate × price_modifier

Consumption captures demand. AMM price captures market conditions.
Together they form a self-correcting loop.

Extracted from ResourceSpawnService (which used a 3-factor formula
with an additional supply_modifier). The supply modifier is intentionally
dropped — tags and caps on targets control distribution, not a
per-player-hour supply target.
"""

import logging
from decimal import Decimal

from blockchain.xrpl.services.spawn.calculators.base import BaseCalculator

logger = logging.getLogger("evennia")


class ResourceCalculator(BaseCalculator):
    """Two-factor resource spawn budget: consumption × price_modifier."""

    def calculate(self, item_type, type_key, **overrides):
        """Calculate hourly spawn budget for a resource.

        Returns int — number of units to spawn this hour.
        """
        cfg = self.get_item_config(item_type, type_key, **overrides)

        # Baseline: 24h rolling average consumption, floored at default
        default_rate = float(cfg["default_spawn_rate"])
        avg_consumption = self._get_avg_consumption(type_key)
        base_rate = max(default_rate, float(avg_consumption))

        # Price modifier from AMM
        buy_price = self._get_latest_buy_price(type_key)
        p_mod = self.price_modifier(buy_price, cfg)

        # Combined budget (2-factor: no supply modifier)
        budget = base_rate * p_mod
        return max(0, round(budget))

    # ================================================================== #
    #  Data queries — extracted from ResourceSpawnService
    # ================================================================== #

    @staticmethod
    def _get_avg_consumption(resource_id):
        """24h rolling average of consumed_1h from ResourceSnapshot.

        Returns Decimal.
        """
        from blockchain.xrpl.currency_cache import get_currency_code
        from blockchain.xrpl.models import ResourceSnapshot

        currency_code = get_currency_code(resource_id)
        if not currency_code:
            return Decimal(0)

        snapshots = (
            ResourceSnapshot.objects.filter(currency_code=currency_code)
            .order_by("-hour")[:24]
        )
        values = [s.consumed_1h for s in snapshots]
        if not values:
            return Decimal(0)
        return sum(values) / len(values)

    @staticmethod
    def _get_latest_buy_price(resource_id):
        """Get the most recent AMM buy price for a resource.

        Returns Decimal or None if no AMM pool exists.
        """
        from blockchain.xrpl.currency_cache import get_currency_code
        from blockchain.xrpl.models import ResourceSnapshot

        currency_code = get_currency_code(resource_id)
        if not currency_code:
            return None

        snapshot = (
            ResourceSnapshot.objects.filter(
                currency_code=currency_code,
                amm_buy_price__isnull=False,
            )
            .order_by("-hour")
            .first()
        )
        return snapshot.amm_buy_price if snapshot else None

    # ================================================================== #
    #  Price modifier — extracted from ResourceSpawnService
    # ================================================================== #

    @staticmethod
    def price_modifier(buy_price, config):
        """Linear interpolation of price within target band.

        Two-segment curve with 1.0 at the midpoint:
          price <= low  → modifier_min
          price = mid   → 1.0
          price >= high → modifier_max

        Returns 1.0 if buy_price is None (no AMM pool).
        """
        if buy_price is None:
            return 1.0

        price = float(buy_price)
        low = float(config["target_price_low"])
        high = float(config["target_price_high"])
        mod_min = float(config["modifier_min"])
        mod_max = float(config["modifier_max"])
        midpoint = (low + high) / 2.0

        if price <= low:
            return mod_min
        elif price >= high:
            return mod_max
        elif price <= midpoint:
            t = (price - low) / (midpoint - low)
            return mod_min + t * (1.0 - mod_min)
        else:
            t = (price - midpoint) / (high - midpoint)
            return 1.0 + t * (mod_max - 1.0)
