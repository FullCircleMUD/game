"""
DistrictMapNFTItem — a tradeable district map NFT.

Each instance represents a partially-surveyed map of a predefined area.
Completion % is visible in the item name at all times (in inventory,
on the ground, in trade/auction) so buyers always see what they're buying.

Transfer rules:
  - Non-cartographer holders: static snapshot, completion % never improves.
  - Cartographer holders: can resume surveying and add more rooms.

One map per map_key in inventory. Bank has no limit — the business model
is: survey → bank → re-enter area → new blank spawns → repeat to build stock.
"""

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.base_nft_item import BaseNFTItem


class DistrictMapNFTItem(BaseNFTItem):
    """
    A parchment map of a predefined district.

    Attributes:
        map_key         — which predefined map this NFT represents
        db.surveyed_points — set of point_key strings the holder has surveyed
    """

    map_key = AttributeProperty("")

    def at_object_creation(self):
        super().at_object_creation()
        self.db.surveyed_points = set()
        self.tags.add("district_map", category="item_type")

    @property
    def surveyed_points(self):
        """Return the set of surveyed point keys, initialising if absent."""
        pts = self.db.surveyed_points
        if pts is None:
            self.db.surveyed_points = set()
            return self.db.surveyed_points
        return pts

    @property
    def completion_pct(self):
        """Return integer 0-100 completion percentage."""
        from world.cartography.map_registry import get_map
        map_def = get_map(self.map_key)
        if not map_def or not map_def.get("point_cells"):
            return 0
        total = len(map_def["point_cells"])
        if total == 0:
            return 0
        surveyed = len(self.surveyed_points)
        return round((surveyed / total) * 100)

    def return_appearance(self, looker, **kwargs):
        """Override appearance to show map-specific desc with usage hint."""
        from world.cartography.map_registry import get_map
        map_def = get_map(self.map_key)
        name = map_def["display_name"] if map_def else (self.map_key or "Unknown Area")
        pct = self.completion_pct
        header = self.get_display_name(looker, **kwargs)
        desc = (
            f"A parchment map of {name}, {pct}% complete. "
            "Careful cartographic notation marks the surveyed areas.\n"
            f"|wType '|ymap {name.lower()}|w' to view it.|n"
        )
        return f"{header}\n{desc}"

    def get_display_name(self, looker=None, **kwargs):
        """Always shows 'Map: <Area> <pct>%' — e.g. 'Map: Millholm Town 37%'."""
        from world.cartography.map_registry import get_map
        map_def = get_map(self.map_key)
        name = map_def["display_name"] if map_def else (self.map_key or "Unknown Area")
        # Self-heal: update key from generic "DistrictMap" to searchable name
        expected_key = f"map of {name}".lower()
        if self.key != expected_key:
            self.key = expected_key
        pct = self.completion_pct
        display = f"Map: {name} {pct}%"
        if looker and self.locks.check_lockstring(looker, "perm(Builder)"):
            return f"{display} |w[NFT #{self.token_id}]|n"
        return display
