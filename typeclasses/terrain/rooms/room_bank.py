# in typeclasses/rooms.py

from typeclasses.terrain.rooms.room_base import RoomBase
from evennia import AttributeProperty
from commands.room_specific_cmds.bank.cmdset_bank import CmdSetBank

class RoomBank(RoomBase):

    allow_combat = AttributeProperty(False, autocreate=False)
    allow_pvp = AttributeProperty(False, autocreate=False)
    # True, despite this being a peaceful room. allow_death=False is the
    # arena mechanic — it routes death to _defeat(), which keeps all gear,
    # gold and XP and teleports the character out on 1 HP. Applied to a
    # safe room it becomes a consequence-dodge: starve here, or run here
    # poisoned from somewhere else, and die for free. allow_combat=False
    # is what makes the room peaceful; it needs no help from this.
    allow_death = AttributeProperty(True, autocreate=False)

    # No Flying
    max_height = AttributeProperty(0) 
    max_depth = AttributeProperty(0)
    
    def at_object_creation(self):
        super().at_object_creation()
        """
        When a cmdset is on the room, Evennia merges it with the character's 
        cmdset dynamically whenever commands are processed. 
        It checks what room the character is in, grabs the room's cmdsets, 
        and merges them on the fly. When the character leaves, 
        the room's cmdsets simply aren't included in the merge anymore.
        """
        self.cmdset.add(CmdSetBank, persistent=True)
    
    def at_object_receive(self, moved_obj, source_location, **kwargs):
        """Called when something enters the room."""

        super().at_object_receive(moved_obj, source_location, **kwargs)

        if moved_obj.has_account:
            moved_obj.msg("\n|c--- Welcome to the Bank ---|n")

