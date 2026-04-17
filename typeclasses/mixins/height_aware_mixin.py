"""
HeightAwareMixin — tracks vertical position within a room.

Composed into every base class that exists within a room's vertical space:
BaseActor, Corpse, BaseNFTItem, WorldFixture, WorldItem.

Rooms and exits are NOT height-aware — they *define* vertical space,
they don't exist within it.

Height-gated visibility is a **room + object** concern:

- Rooms define visibility barriers (``visibility_up_barrier``,
  ``visibility_down_barrier``) — terrain features like canopy, deep
  water, fog layers that block line of sight at a specific height.
- Objects define their ``size`` — small things are concealed by
  barriers, large things are visible regardless.

The check: is there a barrier between observer and object, and is the
object small enough to be concealed?  Same-height objects are always
visible regardless of barriers.
"""

from evennia import AttributeProperty

from enums.size import size_value


class HeightAwareMixin:
    """Tracks vertical position within a room (0=ground, >0=air, <0=underwater)."""

    room_vertical_position = AttributeProperty(0)

    def is_height_visible_to(self, looker):
        """Check if this object is visible to a looker based on height.

        Uses the room's visibility barriers and the object's size.
        Same height → always visible. Otherwise, checks whether a
        barrier lies between observer and object and whether the
        object is small enough to be concealed.

        Returns True if no barriers are set, or if the object is too
        large to be concealed, or if no barrier lies between the two.
        """
        obj_height = getattr(self, "room_vertical_position", 0)
        looker_height = getattr(looker, "room_vertical_position", 0)

        # Same height — always visible
        if looker_height == obj_height:
            return True

        # Get room barriers
        room = getattr(self, "location", None)
        if room is None:
            return True

        obj_size = size_value(getattr(self, "size", "medium"))

        # Observer below object — check up barrier
        if looker_height < obj_height:
            barrier = getattr(room, "visibility_up_barrier", None)
            if barrier is not None:
                b_height, b_max_size = barrier
                if looker_height < b_height <= obj_height:
                    if obj_size <= size_value(b_max_size):
                        return False

        # Observer above object — check down barrier
        if looker_height > obj_height:
            barrier = getattr(room, "visibility_down_barrier", None)
            if barrier is not None:
                b_height, b_max_size = barrier
                if obj_height <= b_height < looker_height:
                    if obj_size <= size_value(b_max_size):
                        return False

        return True
