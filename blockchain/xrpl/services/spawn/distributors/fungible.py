"""
FungibleDistributor — places resources and gold on targets.

Uses FungibleInventoryMixin methods for mobs/containers.
Harvest rooms are a special case — increment resource_count directly.
"""

import logging

from blockchain.xrpl.services.spawn.distributors.base import BaseDistributor

logger = logging.getLogger("evennia")


class ResourceDistributor(BaseDistributor):
    """Distributes resources to tagged targets."""

    tag_name = "spawn_resources"
    category = "resources"
    max_attr_name = "spawn_resources_max"

    def _place(self, target, type_key, amount):
        """Place resources on a target.

        Harvest rooms: increment resource_count directly.
        Mobs/containers: call receive_resource_from_reserve().
        """
        resource_id = int(type_key)

        # Harvest room exception
        if hasattr(target.db, "resource_count") and target.db.resource_count is not None:
            current = target.db.resource_count or 0
            target.db.resource_count = current + amount
            return

        # Mob/container — FungibleInventoryMixin
        target.receive_resource_from_reserve(resource_id, amount)


class GoldDistributor(BaseDistributor):
    """Distributes gold to tagged targets."""

    tag_name = "spawn_gold"
    category = "gold"
    max_attr_name = "spawn_gold_max"

    def _place(self, target, type_key, amount):
        """Place gold on a target via FungibleInventoryMixin."""
        target.receive_gold_from_reserve(amount)
