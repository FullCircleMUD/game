"""
HoldableNFTItem — base typeclass for all NFT-backed holdable items.

Covers shields, torches, orbs, books, lanterns — anything equipped via
the 'hold' command into the HOLD wearslot.

Extends WearableNFTItem to inherit the data-driven wear_effects system
and durability tracking. Stat effects (e.g. AC bonus for shields) are
expressed as wear_effects entries in the prototype data.

Subclass hierarchy:
    WearableNFTItem
    └── HoldableNFTItem (this class)
        └── (future subclasses for complex behaviour)
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.wearslot import HumanoidWearSlot
from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem


class HoldableNFTItem(WearableNFTItem):
    """
    Base class for all holdable NFTs (shields, torches, orbs, etc.).

    Inherits from WearableNFTItem:
        wearslot, wear_effects, max_durability, durability, repairable,
        at_wear/at_remove (data-driven effect loop), at_break (equipment break)
    """

    # Override default wearslot from WearableNFTItem
    wearslot = AttributeProperty(HumanoidWearSlot.HOLD)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("holdable", category="item_type")

    # ================================================================== #
    #  Equip / Unequip Hooks
    # ================================================================== #

    def at_wear(self, wearer):
        """Bridge for BaseWearslotsMixin.wear() — applies effects then delegates to at_hold()."""
        super().at_wear(wearer)  # applies wear_effects
        self.at_hold(wearer)

    def at_hold(self, holder):
        """
        Extension point for holdable-specific equip behaviour.

        Called after wear_effects are applied. Override in holdable
        subclasses for additional behaviour (e.g. torch provides light).

        Args:
            holder: the Evennia object holding this item
        """
        pass

    def at_remove(self, holder):
        """Reverse wear_effects and any holdable-specific cleanup."""
        super().at_remove(holder)
