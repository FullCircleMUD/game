"""
MobItem — base typeclass for all non-NFT mob equipment.

Mirrors BaseNFTItem in the NFT hierarchy but without blockchain
tracking, durability, height awareness, hidden/invisible mechanics,
or item restriction gates.

MobItem instances are deleted on mob death via class-based filtering
in CombatMob._create_corpse() — they never transfer to corpses or
enter the player economy.
"""

from evennia.objects.objects import DefaultObject
from evennia.typeclasses.attributes import AttributeProperty


class MobItem(DefaultObject):
    """
    Base class for all mob-only items (weapons, armour, consumables).

    Stripped vs BaseNFTItem:
        - No HeightAwareMixin (mob's own height handles this)
        - No HiddenObjectMixin (mob hides, gear goes with it)
        - No ItemRestrictionMixin (builders enforce at build time)
        - No DurabilityMixin (mob items are ephemeral)
        - No NFT tracking (no token_id, no NFTService calls)
    """

    weight = AttributeProperty(0.0)

    def reduce_durability(self, amount):
        """No-op — mob items have no durability. Stubbed because
        execute_attack() calls this on every hit and parry."""
        pass
