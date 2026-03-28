"""
HeightAwareMixin — tracks vertical position within a room.

Composed into every base class that exists within a room's vertical space:
BaseActor, Corpse, BaseNFTItem, WorldFixture, WorldItem.

Rooms and exits are NOT height-aware — they *define* vertical space,
they don't exist within it.
"""

from evennia import AttributeProperty


class HeightAwareMixin:
    """Tracks vertical position within a room (0=ground, >0=air, <0=underwater)."""

    room_vertical_position = AttributeProperty(0)
