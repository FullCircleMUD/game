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
    # True, despite this being a peaceful room. allow_death=False is the
    # arena mechanic — it routes death to _defeat(), which keeps all gear,
    # gold and XP and teleports the character out on 1 HP. Applied to a
    # safe room it becomes a consequence-dodge: starve here, or run here
    # poisoned from somewhere else, and die for free. allow_combat=False
    # is what makes the room peaceful; it needs no help from this.
    allow_death = AttributeProperty(True, autocreate=False)

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
