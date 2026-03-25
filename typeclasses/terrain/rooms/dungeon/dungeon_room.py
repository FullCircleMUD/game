"""
DungeonRoom — procedurally generated room inside a dungeon instance.

Extends RoomBase to get combat flags, FungibleInventoryMixin,
visibility filtering, lighting, weather, and terrain integration.
Each room tracks its coordinates and instance.

The ``not_clear`` tag (category ``dungeon_room``) gates forward exit
traversal — players must clear all mobs before proceeding.
"""

from evennia import AttributeProperty

from typeclasses.terrain.rooms.room_base import RoomBase
from commands.room_specific_cmds.dungeon.cmdset_dungeon_room import (
    CmdSetDungeonRoom,
)


class DungeonRoom(RoomBase):
    """A procedurally generated dungeon room."""

    xy_coords = AttributeProperty((0, 0))
    dungeon_instance_id = AttributeProperty(None)
    is_boss_room = AttributeProperty(False)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetDungeonRoom, persistent=True)

    def get_display_footer(self, looker, **kwargs):
        """Show blocked path indicator when room is not cleared."""
        footer = super().get_display_footer(looker, **kwargs)
        if self.tags.has("not_clear", category="dungeon_room"):
            footer += "\n|rThe path forward is blocked!|n"
        return footer
