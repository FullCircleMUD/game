"""
CanteenNFTItem — a small leather canteen for carrying drinking water.

Crafted by leatherworkers (BASIC). Lives in the character's inventory like
bread or potions — NOT in the HOLD slot, so the player can drink without
putting down their weapon or torch. The `drink` command finds it by walking
the inventory.

Capacity: 5 drinks. A drink restores one thirst stage. So a full canteen
lasts roughly half the thirst meter (12 → 7).

Display name shows water level:
    a leather canteen (5/5 drinks)
    a leather canteen (3/5 drinks)
    a leather canteen (empty)
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.mixins.water_container import WaterContainerMixin


DEFAULT_CANTEEN_CAPACITY = 5


class CanteenNFTItem(WaterContainerMixin, BaseNFTItem):
    """
    A leather canteen — small portable water container.

    Inventory item (not held). Refilled at fountains, in natural water
    sources (future), or via the Create Water spell.
    """

    max_capacity = AttributeProperty(DEFAULT_CANTEEN_CAPACITY)
    current = AttributeProperty(DEFAULT_CANTEEN_CAPACITY)

    def at_object_creation(self):
        super().at_object_creation()
        self.db.weight = 0.5  # empty canteen weight in kg
        self.tags.add("water_container", category="item_type")
        self.at_water_container_init()

    def get_display_name(self, looker=None, **kwargs):
        """Append water level to the display name."""
        base = super().get_display_name(looker, **kwargs)
        if self.is_empty:
            return f"{base} |x(empty)|n"
        return f"{base} ({self.get_water_display()})"
