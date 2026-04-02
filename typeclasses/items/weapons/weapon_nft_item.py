"""
WeaponNFTItem — base typeclass for all NFT-backed weapons.

Composes WeaponMechanicsMixin for combat mechanics (damage, hooks,
mastery) and inherits from WearableNFTItem for equipment and durability.

Weapon combat mechanics are defined in WeaponMechanicsMixin so they
can be shared with MobWeapon (non-NFT mob weapons). This class adds
only the NFT-specific equip lifecycle hooks.

Subclass hierarchy:
    WearableNFTItem
    └── WeaponNFTItem (this class)
        └── LongswordNFTItem(LongswordMixin, WeaponNFTItem)
        └── DaggerNFTItem(DaggerMixin, WeaponNFTItem)
        └── ...
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.wearslot import HumanoidWearSlot
from typeclasses.items.wearables.wearable_nft_item import WearableNFTItem
from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin


class WeaponNFTItem(WeaponMechanicsMixin, WearableNFTItem):
    """
    Base class for all weapon NFTs.

    Inherits from WeaponMechanicsMixin:
        base_damage, material, damage_type, weapon_type, speed,
        two_handed, is_finesse, can_dual_wield, is_inset,
        weapon_type_key, get_damage_roll(), get_wielder_mastery(),
        14 combat hooks, 10 mastery-scaled query methods.

    Inherits from WearableNFTItem:
        wearslot, wear_effects (via WearableMixin),
        max_durability, durability (via DurabilityMixin),
        at_break() (NFT-specific break handler).
    """

    # Override default wearslot — weapons go in WIELD
    wearslot = AttributeProperty(HumanoidWearSlot.WIELD)

    def at_object_creation(self):
        super().at_object_creation()
        self.tags.add("weapon", category="item_type")

    # ================================================================== #
    #  Equip / Unequip Hooks
    # ================================================================== #

    def at_wear(self, wearer):
        """Bridge for BaseWearslotsMixin.wear() — applies effects then delegates to at_wield()."""
        super().at_wear(wearer)  # applies wear_effects via WearableMixin
        self.at_wield(wearer)

    def at_wield(self, wielder):
        """
        Extension point for weapon-specific equip behaviour.

        Called after wear_effects are applied. Override in weapon
        subclasses for additional behaviour (e.g. parry setup).

        Args:
            wielder: the Evennia object wielding this weapon
        """
        pass

    def at_remove(self, wielder):
        """Reverse wear_effects and any weapon-specific cleanup."""
        super().at_remove(wielder)
