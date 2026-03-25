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

from evennia.typeclasses.attributes import AttributeProperty

from typeclasses.items.base_nft_item import BaseNFTItem
from typeclasses.mixins.durability import DurabilityMixin


class WearableNFTItem(DurabilityMixin, BaseNFTItem):
    """
    Base class for all equippable NFTs (armor, weapons, holdables, etc.).

    Attributes (from prototype):
        wearslot       — str or list of str, which slot(s) this item fits
                         Uses enum values from enums.wearslot
        wear_effects   — list of effect dicts applied on equip/removed on unequip
        max_durability — int, maximum durability (0 = unbreakable)
        weight         — float, item weight (inherited from BaseNFTItem)

    Attributes (from metadata, mutable per instance):
        durability     — int, current durability
    """

    # Which wearslot(s) this item can be equipped in.
    # Set by prototype. String for single-slot items ("HEAD"),
    # list for multi-slot items (["LEFT_EAR", "RIGHT_EAR"]).
    wearslot = AttributeProperty(None)

    # Data-driven effects applied on equip, reversed on unequip.
    # Each entry is a dict, e.g. {"type": "stat_bonus", "stat": "armor_class", "value": 2}
    wear_effects = AttributeProperty(default=list)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("wearable", category="item_type")
        self.at_durability_init()

    # ================================================================== #
    #  Equip / Unequip Hooks
    # ================================================================== #

    def at_wear(self, wearer):
        """
        Called by BaseWearslotsMixin.wear() after this item is equipped.

        Condition effects are applied incrementally (ref-counted).
        Numeric stat effects are handled by nuclear recalculate — the
        item is already in wearslots when this hook fires, so
        _recalculate_stats() will see it.

        Args:
            wearer: the Evennia object wearing this item
        """
        for effect in self.wear_effects or []:
            if effect.get("type") == "condition":
                wearer.apply_effect(effect)
        wearer._recalculate_stats()

    def at_remove(self, wearer):
        """
        Called by BaseWearslotsMixin.remove() after this item is unequipped.

        Condition effects are removed incrementally (ref-counted).
        Numeric stat effects are handled by nuclear recalculate — the
        item is already out of wearslots when this hook fires.

        Args:
            wearer: the Evennia object removing this item
        """
        for effect in self.wear_effects or []:
            if effect.get("type") == "condition":
                wearer.remove_effect(effect)
        wearer._recalculate_stats()

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
