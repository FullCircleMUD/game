"""
WorldFixture — immovable, non-NFT world object base class.

For signs, chests, decorations, furniture — anything placed in the world
that players cannot pick up and that is NOT blockchain-backed.

Includes HiddenObjectMixin and InvisibleObjectMixin for room appearance
filtering. Subclasses combine these via a unified is_visible_to() check.

Usage:
    class WorldSign(WorldFixture):
        ...
"""

from evennia import AttributeProperty
from evennia.objects.objects import DefaultObject

from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
from typeclasses.mixins.hidden_object import HiddenObjectMixin
from typeclasses.mixins.invisible_object import InvisibleObjectMixin


class WorldFixture(HeightAwareMixin, InvisibleObjectMixin, HiddenObjectMixin, DefaultObject):
    """
    Immovable, non-NFT base class for permanent world objects.

    - Cannot be picked up (get:false lock)
    - Not blockchain-tracked — no token_id, no NFT service hooks
    - Supports hidden and invisible states via mixins
    """

    size = AttributeProperty("medium")

    def at_object_creation(self):
        super().at_object_creation()
        self.locks.add("get:false()")
        self.at_hidden_init()
        self.at_invisible_init()

    def at_pre_get(self, getter, **kwargs):
        getter.msg("You can't pick that up.")
        return False

    def is_visible_to(self, character):
        """
        Combined visibility check across both hidden and invisible states.

        An object is visible only if BOTH checks pass:
            - Hidden check: not hidden, or character has discovered it
            - Invisible check: not invisible, or character has DETECT_INVIS
        """
        if not self.is_hidden_visible_to(character):
            return False
        if not self.is_invis_visible_to(character):
            return False
        return True
