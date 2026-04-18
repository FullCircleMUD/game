"""
ClimbableFixture — a WorldFixture that characters can climb.

Combines ClimbableMixin (data attributes) with WorldFixture (immovable,
non-NFT, hidden/invisible support). Used for drainpipes, ladders, ropes,
vines, trees, and anything else characters can climb to change height.
"""

from evennia import AttributeProperty

from enums.size import Size
from typeclasses.mixins.climbable_mixin import ClimbableMixin
from typeclasses.world_objects.base_fixture import WorldFixture


class ClimbableFixture(ClimbableMixin, WorldFixture):
    """A WorldFixture that characters can climb."""

    size = AttributeProperty(Size.LARGE.value)
