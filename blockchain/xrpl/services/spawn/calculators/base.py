"""
BaseCalculator — interface for all spawn budget calculators.

Every calculator is constructed with the full SPAWN_CONFIG and implements
calculate(item_type, type_key, **overrides) → int.
"""

from abc import ABC, abstractmethod


class BaseCalculator(ABC):
    """Base class for spawn budget calculators."""

    def __init__(self, config):
        """
        Args:
            config: The full SPAWN_CONFIG dict, keyed by (item_type, type_key).
        """
        self.config = config

    def get_item_config(self, item_type, type_key, **overrides):
        """Look up config for a specific item, with optional overrides.

        Args:
            item_type: "resource", "gold", "knowledge", "rare_nft"
            type_key: resource_id, "gold", or item_type_name
            **overrides: Per-call config overrides (tests/admin tuning)

        Returns:
            dict — merged config for this item

        Raises:
            KeyError if (item_type, type_key) not in SPAWN_CONFIG
        """
        base = self.config[(item_type, type_key)]
        if overrides:
            return {**base, **overrides}
        return base

    @abstractmethod
    def calculate(self, item_type, type_key, **overrides):
        """Calculate the hourly spawn budget for an item.

        Args:
            item_type: "resource", "gold", "knowledge", "rare_nft"
            type_key: identifier within namespace
            **overrides: optional per-call config overrides

        Returns:
            int — number of units to spawn this hour
        """
        ...
