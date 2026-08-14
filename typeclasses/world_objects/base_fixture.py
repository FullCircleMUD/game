"""
WorldFixture — immovable, non-NFT world object base class.

For signs, chests, decorations, furniture — anything placed in the world
that players cannot pick up and that is NOT blockchain-backed.

Includes HiddenObjectMixin and InvisibleObjectMixin for room appearance
filtering, both consulted by ``p_object_visible_to``.

Usage:
    class WorldSign(WorldFixture):
        ...
"""

from evennia import AttributeProperty
from evennia.objects.objects import DefaultObject

from enums.size import Size
from typeclasses.mixins.height_aware_mixin import HeightAwareMixin
from typeclasses.mixins.hidden_object import HiddenObjectMixin
from typeclasses.mixins.invisible_object import InvisibleObjectMixin
from typeclasses.mixins.unseen_name import UnseenNameMixin


class WorldFixture(
    UnseenNameMixin,
    HeightAwareMixin,
    InvisibleObjectMixin,
    HiddenObjectMixin,
    DefaultObject,
):
    """
    Immovable, non-NFT base class for permanent world objects.

    - Cannot be picked up (get:false lock)
    - Not blockchain-tracked — no token_id, no NFT service hooks
    - Supports hidden and invisible states via mixins
    """

    size = AttributeProperty(Size.MEDIUM.value)

    def at_object_creation(self):
        super().at_object_creation()
        self.locks.add("get:false()")
        self.at_hidden_init()
        self.at_invisible_init()

    def at_pre_get(self, getter, **kwargs):
        getter.msg("You can't pick that up.")
        return False
