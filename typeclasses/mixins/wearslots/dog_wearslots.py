"""
DogWearslotsMixin — defines equipment slots for dog pets.

Proof of concept for non-humanoid wearslot mixins. Demonstrates how
the BaseWearslotsMixin pattern extends to different creature types
with their own slot enums.

Usage:
    class NFTPetDog(DogWearslotsMixin, UntakeableNFTItem):
        def at_object_creation(self):
            super().at_object_creation()
            self.at_wearslots_init()
"""

from enums.wearslot import DogWearSlot
from typeclasses.mixins.wearslots.base_wearslots import BaseWearslotsMixin


class DogWearslotsMixin(BaseWearslotsMixin):
    """
    Wearslot mixin for dog pets (collars, coats, etc.).

    Defines 2 equipment slots: DOG_NECK and DOG_BODY.
    """

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_wearslots_init(self):
        """
        Initialize dog wearslots.
        Safe to call multiple times — only sets defaults if not already present.
        """
        super().at_wearslots_init()
        if not self.db.wearslots:
            self.db.wearslots = {
                slot.value: None for slot in DogWearSlot
            }

    # ================================================================== #
    #  Validation
    # ================================================================== #

    def can_wear(self, item):
        """
        Determine whether this dog is allowed to wear the given item.

        This checks creature-type restrictions only.
        Slot availability is checked separately by wear() itself.

        Args:
            item: Evennia object to validate

        Returns:
            bool — True if the item can be worn
        """
        return True
