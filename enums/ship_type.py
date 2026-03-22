"""Ship type enum — maps ship names to mastery tier values."""

from enum import Enum


class ShipType(Enum):
    COG = 1          # BASIC
    CARAVEL = 2      # SKILLED
    BRIGANTINE = 3   # EXPERT
    CARRACK = 4      # MASTER
    GALLEON = 5      # GRANDMASTER

    @property
    def item_type_name(self):
        """NFTItemType name in the database (e.g. 'Cog', 'Caravel')."""
        return self.name.capitalize()
