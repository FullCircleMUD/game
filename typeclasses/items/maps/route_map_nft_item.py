"""
RouteMapNFTItem — a tradeable route map NFT.

Represents knowledge of a specific interzone route. Produced by the
``explore`` command on successful discovery. Required by ``travel``
and ``sail`` to use known routes — the map IS the knowledge.

The map is a simple proof-of-knowledge token. No special mechanics
beyond identifying which route it represents. Trade it, bank it,
give it away — whoever holds it can travel the route.

Route maps are NOT district maps (DistrictMapNFTItem). District maps
track surveyed rooms within a zone. Route maps unlock zone-to-zone travel.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.base_nft_item import BaseNFTItem


class RouteMapNFTItem(BaseNFTItem):
    """
    A parchment chart showing a route between two gateway locations.

    Attributes:
        route_key        — unique route identifier (``<gateway_key>:<dest_key>``)
        departure_name   — display name of the departure gateway
        destination_name — display name of the destination
    """

    route_key = AttributeProperty("")
    departure_name = AttributeProperty("")
    destination_name = AttributeProperty("")

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("route_map", category="item_type")

    def get_display_name(self, looker=None, **kwargs):
        """Show 'Route Map: Departure → Destination'."""
        dep = self.departure_name or "Unknown"
        dest = self.destination_name or "Unknown"
        display = f"Route Map: {dep} → {dest}"
        if looker and self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"{display} |w[NFT #{self.token_id}]|n"
        return display

    def return_appearance(self, looker, **kwargs):
        """Show route details and usage hint when looked at."""
        header = self.get_display_name(looker, **kwargs)
        dep = self.departure_name or "Unknown"
        dest = self.destination_name or "Unknown"
        desc = (
            f"A carefully drawn chart showing the route from {dep} to {dest}. "
            "Holding this map allows you to travel or sail this route."
        )
        return f"{header}\n{desc}"
