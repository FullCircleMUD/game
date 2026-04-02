"""
MobHoldable — base typeclass for mob-only holdable items.

Mirrors HoldableNFTItem in the NFT hierarchy: equips in the HOLD
slot, supports wear_effects (e.g. AC bonus for shields).

No durability, no NFT tracking — mob holdables are ephemeral
and deleted on mob death.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.wearslot import HumanoidWearSlot
from typeclasses.items.mob_items.mob_wearable import MobWearable


class MobHoldable(MobWearable):
    """
    Base class for mob-only holdable items (shields, torches, orbs).

    Inherits from MobWearable:
        wearslot, wear_effects (via WearableMixin),
        weight, reduce_durability() no-op (via MobItem).
    """

    # Holdables go in HOLD slot
    wearslot = AttributeProperty(HumanoidWearSlot.HOLD)

    def at_wear(self, wearer):
        """Bridge — applies wear_effects then delegates to at_hold()."""
        super().at_wear(wearer)
        self.at_hold(wearer)

    def at_hold(self, holder):
        """Extension point for holdable-specific equip behaviour."""
        pass

    def at_remove(self, holder):
        """Reverse wear_effects and any holdable-specific cleanup."""
        super().at_remove(holder)
