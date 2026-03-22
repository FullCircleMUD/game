"""
DungeonEntranceRoom — a fixed room placed by builders that serves as the
entry point for a procedural dungeon (command-triggered entry).

Stores the dungeon_template_id and injects the CmdSetDungeonEntrance
so players can use `enter dungeon` to start an instance.

For movement-triggered entry, use DungeonTriggerExit instead.
The entry trigger is determined by builder placement, not by the template —
the same template can be used with either mechanism.
"""

from evennia import AttributeProperty

from typeclasses.terrain.rooms.room_base import RoomBase
from commands.room_specific_cmds.dungeon.cmdset_dungeon_entrance import (
    CmdSetDungeonEntrance,
)


class DungeonEntranceRoom(RoomBase):
    """Fixed entrance room for a procedural dungeon."""

    dungeon_template_id = AttributeProperty(None)
    dungeon_destination_room_id = AttributeProperty(None)  # passage endpoint

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetDungeonEntrance, persistent=True)
