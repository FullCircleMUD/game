"""
KnowledgeCalculator — gap-based budget for knowledge NFTs.

    budget = max(0, eligible_players - known_by - unlearned_copies)

Spell scrolls and recipe scrolls are permanent knowledge — once learned,
they never leave the game. The budget equals the exact number of players
who still need the scroll/recipe, based on the latest hourly saturation
snapshot.

Self-correcting: scrolls spawned in hour N are counted as unlearned_copies
in the hour N+1 snapshot, closing the gap. No over-spawning even for
small gaps (e.g. 1 new GM evocation player).
"""

import logging

from blockchain.xrpl.services.spawn.calculators.base import BaseCalculator

logger = logging.getLogger("evennia")


class KnowledgeCalculator(BaseCalculator):
    """Gap-based spawn budget for spell scrolls and recipe scrolls."""

    def calculate(self, item_type, type_key, **overrides):
        """Calculate hourly spawn budget for a knowledge item.

        Budget = the number of players who don't have this scroll/recipe
        and don't already have an unlearned copy in hand.

        Returns int — number of scrolls to spawn this hour.
        """
        snapshot = self._get_snapshot(type_key)
        if snapshot is None:
            return 0

        gap = snapshot.eligible_players - snapshot.known_by - snapshot.unlearned_copies
        return max(0, gap)

    # ================================================================== #
    #  Saturation query
    # ================================================================== #

    @staticmethod
    def _get_saturation(item_key):
        """Get the latest saturation value for a knowledge item.

        Returns float (0.0-1.0) or None if no snapshot exists or
        eligible_players == 0.
        """
        snapshot = KnowledgeCalculator._get_snapshot(item_key)
        if snapshot is None:
            return None
        return snapshot.saturation

    @staticmethod
    def _get_snapshot(item_key):
        """Get the latest SaturationSnapshot for a knowledge item.

        Returns the snapshot object or None if no snapshot exists or
        eligible_players == 0.
        """
        from blockchain.xrpl.models import SaturationSnapshot

        snapshot = (
            SaturationSnapshot.objects.filter(item_key=item_key)
            .order_by("-hour")
            .first()
        )
        if not snapshot:
            return None

        if snapshot.eligible_players <= 0:
            return None

        return snapshot
