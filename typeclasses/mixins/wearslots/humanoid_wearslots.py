"""
HumanoidWearslotsMixin — defines equipment slots for humanoid characters.

Inherits all wear/remove/query logic from BaseWearslotsMixin and adds
the standard humanoid slot layout (head to toe, plus wield/hold).

Slot names come from the HumanoidWearSlot enum — the single source of
truth for valid humanoid slot names. Items declare which slot(s) they
fit using the same enum values.

Usage:
    class FCMCharacter(FungibleInventoryMixin, HumanoidWearslotsMixin, DefaultCharacter):
        def at_object_creation(self):
            super().at_object_creation()
            self.at_fungible_init()
            self.at_wearslots_init()
"""

from enums.wearslot import HumanoidWearSlot
from typeclasses.mixins.wearslots.base_wearslots import BaseWearslotsMixin


class HumanoidWearslotsMixin(BaseWearslotsMixin):
    """
    Wearslot mixin for humanoid characters (players, humanoid NPCs/mobs).

    Defines 19 equipment slots from head to toe plus WIELD and HOLD.
    """

    # ================================================================== #
    #  Initialization
    # ================================================================== #

    def at_wearslots_init(self):
        """
        Initialize humanoid wearslots.
        Safe to call multiple times — only sets defaults if not already present.
        """
        super().at_wearslots_init()
        if not self.db.wearslots:
            self.db.wearslots = {
                slot.value: None for slot in HumanoidWearSlot
            }

    # ================================================================== #
    #  Validation
    # ================================================================== #

    def can_wear(self, item):
        """
        Determine whether this humanoid creature type can wear the item.

        Creature-type restrictions only (e.g. humanoid vs dog slot
        compatibility). Class, race, level, and attribute restrictions
        are handled by ItemRestrictionMixin.can_use() on the item,
        called earlier in the wear() chain.

        Args:
            item: Evennia object to validate

        Returns:
            bool — True if the item can be worn
        """
        return True
