"""
WorldItem — takeable, non-NFT item base class.

For keys, quest items, novelty items — anything a player can pick up
and carry but that is NOT blockchain-backed and cannot be exported.

Usage:
    class KeyItem(WorldItem):
        ...
"""

from evennia import AttributeProperty
from evennia.objects.objects import DefaultObject

from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
from typeclasses.mixins.hidden_object import HiddenObjectMixin


class WorldItem(HeightAwareMixin, HiddenObjectMixin, DefaultObject):
    """
    Takeable, non-NFT item. Can be picked up, dropped, given, banked,
    but NOT exported to the blockchain.

    Attributes:
        can_export: Always False — export command checks this.
        can_bank: Whether this item can be deposited in AccountBank.
    """

    size = AttributeProperty("small")
    can_export = AttributeProperty(False)
    can_bank = AttributeProperty(True)

    def at_object_creation(self):
        super().at_object_creation()
        self.at_hidden_init()
        # Default Evennia lock allows get — no override needed

    def is_visible_to(self, character):
        """Hidden-state visibility check for room display filtering."""
        return self.is_hidden_visible_to(character)
