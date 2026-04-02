"""
MobWeapon — base typeclass for mob-only weapons.

Mirrors WeaponNFTItem in the NFT hierarchy: composes
WeaponMechanicsMixin for full combat mechanics (damage resolution,
mastery helpers, 14 combat hooks, 10 mastery-scaled query methods).

Concrete mob weapons inherit from both a weapon identity mixin
(e.g. DaggerMixin, LongswordMixin) and this class:

    class MobDagger(DaggerMixin, MobWeapon):
        pass

This gives mob weapons identical combat behaviour to player NFT
weapons — same mastery tables, same hooks, same damage — defined
once in the shared mixin.
"""

from evennia.typeclasses.attributes import AttributeProperty

from enums.wearslot import HumanoidWearSlot
from typeclasses.items.mob_items.mob_wearable import MobWearable
from typeclasses.items.weapons.weapon_mechanics_mixin import WeaponMechanicsMixin


class MobWeapon(WeaponMechanicsMixin, MobWearable):
    """
    Base class for mob-only weapons.

    Inherits from WeaponMechanicsMixin:
        base_damage, material, damage_type, weapon_type, speed,
        two_handed, is_finesse, can_dual_wield, weapon_type_key,
        get_damage_roll(), get_wielder_mastery(), 14 combat hooks,
        10 mastery-scaled query methods.

    Inherits from MobWearable:
        wearslot, wear_effects (via WearableMixin),
        weight, reduce_durability() no-op (via MobItem).
    """

    # Weapons go in WIELD slot
    wearslot = AttributeProperty(HumanoidWearSlot.WIELD)

    def at_wear(self, wearer):
        """Bridge — applies wear_effects then delegates to at_wield()."""
        super().at_wear(wearer)
        self.at_wield(wearer)

    def at_wield(self, wielder):
        """Extension point for weapon-specific equip behaviour."""
        pass

    def at_remove(self, wielder):
        """Reverse wear_effects and any weapon-specific cleanup."""
        super().at_remove(wielder)
