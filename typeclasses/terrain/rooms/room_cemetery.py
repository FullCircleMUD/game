"""
Cemetery room — where characters respawn after death.

Safe room with no combat. Characters bind to a cemetery via the
`bind` command, setting it as their respawn point on death.
"""

from evennia import AttributeProperty

from typeclasses.terrain.rooms.room_base import RoomBase
from commands.room_specific_cmds.cemetery.cmdset_cemetery import CmdSetCemetery


class RoomCemetery(RoomBase):

    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    allow_death = AttributeProperty(False, autocreate=False)

    # Gold cost to bind to this cemetery (0 = free)
    bind_cost = AttributeProperty(1)

    def at_object_creation(self):
        super().at_object_creation()
        self.cmdset.add(CmdSetCemetery, persistent=True)
        self.db.desc = (
            "Weathered gravestones and crumbling monuments dot this quiet clearing. "
            "A faint mist clings to the ground, and the air is still. "
            "This is a place of rest — and of new beginnings."
        )
