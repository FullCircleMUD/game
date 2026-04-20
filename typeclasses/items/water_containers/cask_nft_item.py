"""
CaskNFTItem — a wooden cask for carrying drinking water.

Crafted by carpenters at SKILLED mastery (a step above the leatherworker
canteen). Lives in the character's inventory like bread or potions — NOT
in the HOLD slot, so the player can drink without putting down their
weapon or torch. The `drink` command finds it by walking the inventory.

Capacity: 10 drinks (twice a canteen). A drink restores one thirst stage,
so a full cask covers most of the thirst meter without a refill — at the
cost of being heavier than a canteen and requiring a more skilled
crafter.

Display name shows water level:
    a wooden cask (10/10 drinks)
    a wooden cask (6/10 drinks)
    a wooden cask (empty)
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.mixins.water_container import WaterContainerMixin


DEFAULT_CASK_CAPACITY = 10


class CaskNFTItem(WaterContainerMixin, BaseNFTItem):
    """
    A wooden cask — larger portable water container.

    Inventory item (not held). Twice the capacity of a canteen, heavier,
    and requires a SKILLED carpenter to craft.
    """

    max_capacity = AttributeProperty(DEFAULT_CASK_CAPACITY)
    current = AttributeProperty(DEFAULT_CASK_CAPACITY)

    def at_object_creation(self):
        super().at_object_creation()
        self.db.weight = 2.0  # empty cask weight in kg
        self.tags.add("water_container", category="item_type")
        self.at_water_container_init()

    def get_display_name(self, looker=None, **kwargs):
        """Append water level to the display name."""
        base = super().get_display_name(looker, **kwargs)
        if self.is_empty:
            return f"{base} |x(empty)|n"
        return f"{base} ({self.get_water_display()})"
