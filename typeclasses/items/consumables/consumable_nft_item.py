"""
ConsumableNFTItem — base typeclass for all single-use NFT items.

Sibling to WearableNFTItem in the item hierarchy (both inherit from
BaseNFTItem). Consumables have no wearslot, no durability, no wear_effects.

Subclasses override at_consume() to implement their effect (learn recipe,
heal HP, apply buff, etc.). The consume() method calls at_consume() and
deletes the item on success — BaseNFTItem.at_object_delete() handles the
mirror transition (CHARACTER → RESERVE).

Hierarchy:
    BaseNFTItem
    ├── ConsumableNFTItem      ← this class
    │   ├── CraftingRecipeNFTItem
    │   └── (future: PotionNFTItem, FoodNFTItem, SpellScrollNFTItem)
    └── WearableNFTItem
        └── WeaponNFTItem / HoldableNFTItem
"""

from typeclasses.items.base_nft_item import BaseNFTItem


class ConsumableNFTItem(BaseNFTItem):
    """Base class for all consumable NFTs (recipes, potions, food, scrolls)."""

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("consumable", category="item_type")

    def at_consume(self, consumer):
        """
        Override in subclasses. Called by consume() before deletion.

        Args:
            consumer: the character consuming this item

        Returns:
            (bool, str) — (success, message)
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement at_consume()"
        )

    def consume(self, consumer):
        """
        Consume this item — calls at_consume then deletes on success.

        Args:
            consumer: the character consuming this item

        Returns:
            (bool, str) — (success, message)
        """
        success, msg = self.at_consume(consumer)
        if success:
            self.delete()  # BaseNFTItem.at_object_delete → CHARACTER → RESERVE
        return (success, msg)
