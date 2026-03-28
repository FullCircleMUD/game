"""
ClimbableMixin — data mixin for fixtures that characters can climb.

Declares the attributes that CmdClimb and _check_fall() inspect.
No methods — all logic lives in the command and the fall check.

Usage:
    class ClimbableFixture(ClimbableMixin, WorldFixture):
        pass

    drainpipe = create_object(ClimbableFixture, key="a drainpipe", ...)
    drainpipe.climbable_heights = {0, 1}
    drainpipe.climb_dc = 0
"""

from evennia.typeclasses.attributes import AttributeProperty


class ClimbableMixin:
    """Data mixin marking an object as climbable."""

    climbable_heights = AttributeProperty(None, autocreate=False)
    climb_dc = AttributeProperty(0)
    climb_up_msg = AttributeProperty("You climb upwards.")
    climb_down_msg = AttributeProperty("You climb downwards.")
    climb_fail_msg = AttributeProperty(
        "You fail to get a grip and slip back."
    )
