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

    # ================================================================== #
    #  Display
    # ================================================================== #

    def empty_slot_note(self, slot, looker=None, is_dark=False):
        """
        Report the HOLD slot as consumed by a two-handed wielded weapon.

        A two-handed weapon occupies only the WIELD slot, so HOLD is still
        empty in the wearslots dict even though `hold` will refuse to use
        it (see CmdHold). This tells the equipment display why.

        Args:
            slot: str — the wearslot name being rendered
            looker: object or None — the character viewing
            is_dark: bool — whether the looker is in darkness

        Returns:
            str — the note, or "" for no note
        """
        if slot != HumanoidWearSlot.HOLD.value:
            return ""
        wielded = self.get_slot(HumanoidWearSlot.WIELD)
        if not wielded or not getattr(wielded, "two_handed", False):
            return ""
        name = self.visible_item_name(wielded, looker=looker, is_dark=is_dark)
        return f"{name} is two handed"
