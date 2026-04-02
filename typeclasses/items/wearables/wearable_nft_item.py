"""
WearableNFTItem — base typeclass for all NFT-backed equippable items.

Covers armor, clothing, jewelry, cloaks, and serves as the base class
for WeaponNFTItem (WIELD) and HoldableNFTItem (HOLD).

Data-driven effect system:
    Items store a wear_effects list — each entry is a dict describing
    one effect to apply/remove when the item is equipped/unequipped.
    Example: [{"type": "stat_bonus", "stat": "armor_class", "value": 2}]

    The at_wear/at_remove hooks loop over wear_effects and call
    apply_effect/remove_effect on the wearer. No subclass needed for
    simple stat-mod items — just put the effects in the prototype data.

    Complex items can still subclass and override at_wear/at_remove.

Durability:
    Uses DurabilityMixin. max_durability defaults to 100 for equipment
    (override in prototype for specific items). At 0 durability, the
    item breaks: unequipped, effects reversed, NFT returned to reserve.

Subclass hierarchy:
    WearableNFTItem (this class)
    ├── WeaponNFTItem      (damage, speed, combat hooks)
    │   └── LongswordNFTItem
    ├── HoldableNFTItem    (shields, torches, orbs)
    └── (future subclasses for complex behaviour)
"""

from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.mixins.durability import DurabilityMixin
from typeclasses.mixins.wearable_mixin import WearableMixin


class WearableNFTItem(DurabilityMixin, WearableMixin, BaseNFTItem):
    """
    Base class for all equippable NFTs (armor, weapons, holdables, etc.).

    Inherits from WearableMixin:
        wearslot, wear_effects, at_wear/at_remove (equip/unequip hooks)

    Inherits from DurabilityMixin:
        max_durability, durability, reduce_durability(), at_break()

    Attributes (from prototype):
        max_durability — int, maximum durability (0 = unbreakable)
        weight         — float, item weight (inherited from BaseNFTItem)

    Attributes (from metadata, mutable per instance):
        durability     — int, current durability
    """

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("wearable", category="item_type")
        self.at_durability_init()

    # ================================================================== #
    #  Durability — at_break implementation
    # ================================================================== #

    def at_break(self):
        """
        Equipment breaks at 0 durability: unequip, reverse effects,
        return NFT to reserve pool, delete Evennia object.
        """
        owner = self.location

        if owner and hasattr(owner, "msg"):
            owner.msg(f"|r{self.key} breaks and is destroyed!|n")

        if owner and hasattr(owner, "location") and owner.location:
            owner.location.msg_contents(
                f"{owner.key}'s {self.key} shatters!", exclude=[owner]
            )

        # Reverse wear effects if currently equipped
        if owner and hasattr(owner, "is_worn") and owner.is_worn(self):
            owner.remove(self)  # calls at_remove → reverses wear_effects

        # delete() triggers at_object_delete → NFTService transitions to RESERVE
        self.delete()
