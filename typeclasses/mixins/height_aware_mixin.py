"""
HeightAwareMixin — tracks vertical position within a room.

Composed into every base class that exists within a room's vertical space:
BaseActor, Corpse, BaseNFTItem, WorldFixture, WorldItem.

Rooms and exits are NOT height-aware — they *define* vertical space,
they don't exist within it.

Optional height-gated visibility: set visible_min_height / visible_max_height
to restrict which observers can see this object based on their height.
None = no restriction (default, visible at all heights).
"""

from evennia import AttributeProperty


class HeightAwareMixin:
    """Tracks vertical position within a room (0=ground, >0=air, <0=underwater)."""

    room_vertical_position = AttributeProperty(0)

    # Opt-in height-gated visibility. None = visible at all heights.
    visible_min_height = AttributeProperty(None, autocreate=False)
    visible_max_height = AttributeProperty(None, autocreate=False)

    def is_height_visible_to(self, looker):
        """Check if this object is visible to a looker based on height.

        Returns True if no height gate is set, or if the looker's
        room_vertical_position is within the visible range.
        """
        min_h = self.visible_min_height
        max_h = self.visible_max_height
        if min_h is None and max_h is None:
            return True
        height = getattr(looker, "room_vertical_position", 0)
        if min_h is not None and height < min_h:
            return False
        if max_h is not None and height > max_h:
            return False
        return True
