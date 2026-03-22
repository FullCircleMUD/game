"""
LanternNFTItem — a reusable light source that requires fuel (oil/wheat).

Lanterns are held in the HOLD slot. When lit they burn fuel, but unlike
torches they are NOT destroyed when fuel runs out — they just go dark
and need to be refueled.

Refueled via the 'refuel' command, which consumes 1 wheat (oil substitute)
from the player's fungible inventory.

Display name shows lit/fuel status:
    a lantern (lit, 25:30 remaining)
    a lantern (unlit, empty)
    a lantern (unlit, 15:00 remaining)
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.holdables.holdable_nft_item import HoldableNFTItem
from typeclasses.mixins.light_source import LightSourceMixin


# Default burn time: 30 real minutes = 1800 seconds
DEFAULT_LANTERN_FUEL = 1800


class LanternNFTItem(LightSourceMixin, HoldableNFTItem):
    """
    A reusable NFT lantern. NOT destroyed when fuel runs out.
    """

    is_consumable_light = False

    max_fuel = AttributeProperty(DEFAULT_LANTERN_FUEL)
    fuel_remaining = AttributeProperty(DEFAULT_LANTERN_FUEL)

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
        elif self.fuel_remaining <= 0:
            return f"{base} (unlit, empty)"
        elif self.fuel_remaining >= self.max_fuel:
            return f"{base} (unlit, full)"
        else:
            fuel = self.get_fuel_display()
            return f"{base} (unlit, {fuel} remaining)"
