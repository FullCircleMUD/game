"""
TorchNFTItem — a consumable light source that burns down and is destroyed.

Torches are held in the HOLD slot. When held they can be lit via the
'light' command. They burn for a set duration (default 10 real minutes),
can be extinguished and re-lit later (preserving fuel), and are destroyed
when fuel reaches zero.

Display name shows lit/unlit status and remaining fuel:
    a torch (lit, 8:30 remaining)
    a torch (unlit, 4:15 remaining)
    a torch (unlit, full)
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
from typeclasses.mixins.light_source import LightSourceMixin


# Default burn time: 10 real minutes = 600 seconds
DEFAULT_TORCH_FUEL = 600


class TorchNFTItem(LightSourceMixin, HoldableNFTItem):
    """
    A consumable NFT torch. Destroyed when fuel runs out.
    """

    is_consumable_light = True

    max_fuel = AttributeProperty(DEFAULT_TORCH_FUEL)
    fuel_remaining = AttributeProperty(DEFAULT_TORCH_FUEL)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("light_source", category="item_type")
        self.at_light_init()

    def get_display_name(self, looker=None, **kwargs):
        """Append lit/fuel status to the display name."""
        base = super().get_display_name(looker, **kwargs)
        if self.is_lit:
            fuel = self.get_fuel_display()
            return f"{base} |y(lit, {fuel} remaining)|n"
        elif self.fuel_remaining >= self.max_fuel:
            return f"{base} (unlit, full)"
        elif self.fuel_remaining > 0:
            fuel = self.get_fuel_display()
            return f"{base} (unlit, {fuel} remaining)"
        else:
            return f"{base} (spent)"
