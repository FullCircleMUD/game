"""
RareNFTCalculator — placeholder calculator for rare/legendary items.

Returns a fixed budget from config. Full implementation (population-gated
rules, time-based scarcity) will be designed when rare items are ready.
"""

from blockchain.xrpl.services.spawn.calculators.base import BaseCalculator


class RareNFTCalculator(BaseCalculator):
    """Placeholder rare NFT calculator — returns fixed spawn_rate."""

    def calculate(self, item_type, type_key, **overrides):
        """Return the configured fixed spawn rate.

        Config keys:
            spawn_rate (int): Fixed units per hour. Default 1.
        """
        cfg = self.get_item_config(item_type, type_key, **overrides)
        return max(0, int(cfg.get("spawn_rate", 1)))
