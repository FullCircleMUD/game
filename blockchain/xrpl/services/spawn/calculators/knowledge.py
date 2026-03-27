"""
KnowledgeCalculator — saturation-based budget for knowledge NFTs.

    budget = base_drop_rate × max(0, 1.0 - saturation)

Spell scrolls and recipe scrolls are permanent knowledge — once learned,
they never leave the game. The saturation model adapts drop rates to
what's already known across the eligible player base.

Self-correcting: 100% saturation → budget = 0. New eligible players
→ saturation drops, spawning resumes. Zero eligible players → zero budget.
"""

import logging

from blockchain.xrpl.services.spawn.calculators.base import BaseCalculator

logger = logging.getLogger("evennia")


class KnowledgeCalculator(BaseCalculator):
    """Saturation-based spawn budget for spell scrolls and recipe scrolls."""

    def calculate(self, item_type, type_key, **overrides):
        """Calculate hourly spawn budget for a knowledge item.

        Returns int — number of scrolls to spawn this hour.
        """
        cfg = self.get_item_config(item_type, type_key, **overrides)
        base_drop_rate = float(cfg["base_drop_rate"])

        # Get latest saturation for this item
        saturation = self._get_saturation(type_key)
        if saturation is None:
            # No snapshot data yet — eligible_players might be 0
            return 0

        weight = max(0, 1.0 - saturation)
        budget = base_drop_rate * weight
        return max(0, round(budget))

    # ================================================================== #
    #  Saturation query
    # ================================================================== #

    @staticmethod
    def _get_saturation(item_key):
        """Get the latest saturation value for a knowledge item.

        Returns float (0.0-1.0) or None if no snapshot exists or
        eligible_players == 0.
        """
        from blockchain.xrpl.models import SaturationSnapshot

        snapshot = (
            SaturationSnapshot.objects.filter(item_key=item_key)
            .order_by("-day")
            .first()
        )
        if not snapshot:
            return None

        # Zero eligible players → zero budget (return None triggers 0)
        if snapshot.eligible_players <= 0:
            return None

        return snapshot.saturation
