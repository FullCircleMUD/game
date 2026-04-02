"""
MobWearable — base typeclass for mob-only equippable items.

Mirrors WearableNFTItem in the NFT hierarchy: composes WearableMixin
for wearslot assignment and data-driven wear_effects with nuclear
recalculate integration.

No durability, no NFT tracking, no at_break() — mob wearables are
ephemeral and deleted on mob death.
"""

from typeclasses.items.mob_items.mob_item import MobItem
from typeclasses.mixins.wearable_mixin import WearableMixin


class MobWearable(WearableMixin, MobItem):
    """
    Base class for mob-only equippable items (armour, shields, weapons).

    Inherits from WearableMixin:
        wearslot, wear_effects, at_wear/at_remove
    Inherits from MobItem:
        weight, reduce_durability() no-op
    """
    pass
